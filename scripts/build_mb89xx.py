#!/usr/bin/env python3
"""Build MB-89xx: plasma cell-free RNA fibrosis family (S-BSST1614).

Per ANALYSIS_PLAN_MB89xx.md (frozen 2026-10-29):
- Cohort 1 (n=112, biopsy-anchored) -> MB-8901/8902/8905 frozen test.
- Cohort 2 NAFLD-etiology subset, one sample per Subject_ID (n=179 planned)
  -> MB-8911/8912/8915 external holdout.
- Panel: top-200 MAD genes internal to each corpus; CPM -> log1p -> per-sample
  z-score; label provenance flagged per item.
- Join discipline: matrix column RNAxxxxx <-> annotation SMAPLE_RNA, verified
  exactly; SystemExit on any mismatch (the freeze-16 off-by-one lesson).

Sources (download first, or place under data/sbsst1614/):
  curl -L "https://ftp.ebi.ac.uk/biostudies/fire/S-BSST/614/S-BSST1614/Files/htseq_cohort1.txt" -o data/sbsst1614/htseq_cohort1.txt
  curl -L "https://ftp.ebi.ac.uk/biostudies/fire/S-BSST/614/S-BSST1614/Files/htseq_cohort2.txt" -o data/sbsst1614/htseq_cohort2.txt
  curl -L "https://zenodo.org/records/19047046/files/annotation_cohort1.csv?download=1" -o data/sbsst1614/annotation_cohort1.csv
  curl -L "https://zenodo.org/records/19047046/files/annotation_cohort2.csv?download=1" -o data/sbsst1614/annotation_cohort2.csv

Outputs: prompts/MB-89xx_plasmacf_test.jsonl.gz,
prompts/MB-89xx_plasmacf_ext_test.jsonl.gz, MANIFEST v3-freeze-17 update.

Dry-run (no writes to the project): MASLD_LLM_ROOT=/tmp/dryroot python3 build_mb89xx.py
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import sys
import zlib
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import chi2_contingency

ROOT = Path(os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]))
DATA = ROOT / "data" / "sbsst1614"
PROMPTS = ROOT / "prompts"
MANIFEST = PROMPTS / "MANIFEST.json"
SEED = 20260929
PANEL_N = 200

VERBALIZATIONS = [
    "The following data come from a plasma cell-free RNA (cfRNA) transcriptome profile.\n",
    "Below is a bulk RNA-seq profile of plasma cell-free RNA.\n",
    "A plasma-derived cell-free transcriptomic profile follows.\n",
]
TASK_HEADERS = {
    "MB-8901": (
        "Patient: plasma cfRNA profile.\nGene expression (cfRNA): {genes}\n"
        "Based on this profile, does the patient have advanced liver fibrosis "
        "(stage F3-F4 rather than F0-F2)? Answer yes or no."
    ),
    "MB-8902": (
        "Patient: plasma cfRNA profile.\nGene expression (cfRNA): {genes}\n"
        "Which liver fibrosis stage does this profile indicate? Answer with "
        "one of F0, F1, F2, F3, F4."
    ),
    "MB-8905": (
        "Patient: plasma cfRNA profile.\nGene expression (cfRNA): {genes}\n"
        "Estimate the liver fibrosis stage on the ordinal scale 0 to 4. "
        "Answer with a single number 0, 1, 2, 3, or 4."
    ),
}
EXT_TASKS = {"MB-8901": "MB-8911", "MB-8902": "MB-8912", "MB-8905": "MB-8915"}
AMC_TASKS = {"MB-8901": "MB-8921", "MB-8902": "MB-8922", "MB-8905": "MB-8925"}
NAFLD_ETIOLOGIES = {
    "Non-alcoholic fatty liver (NAFL)",
    "Metabolic syndrome",
    "Diabetes mellitus",
    "Obesity (BMI ≥ 30)",
}
F_STAGES = {"F0": 0, "F1": 1, "F2": 2, "F3": 3, "F4": 4}


def sha16(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def load_matrix(path: Path) -> tuple[list[str], list[str], np.ndarray]:
    """Space-delimited htseq counts; header carries an ensembl_gene_id label.

    Returns (sample_ids, gene_ids, matrix genes x samples). Fails loudly on
    any header/matrix shape ambiguity (freeze-16 discipline).
    """
    with open(path) as f:
        names = f.readline().split()
        gene_ids: list[str] = []
        rows: list[list[float]] = []
        n_bad = 0
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            gene_ids.append(parts[0])
            try:
                rows.append([float(x) for x in parts[1:]])
            except ValueError:
                n_bad += 1
                continue
    mat = np.array(rows, dtype=np.float32)  # genes x samples
    n_val = mat.shape[1]
    looks_like_gene_label = names[0].upper().startswith(("ENSG", "ENSEMBL", "GENE"))
    if len(names) == n_val and not looks_like_gene_label:
        samples = names
    elif len(names) == n_val + 1 and looks_like_gene_label:
        samples = names[1:]
    else:
        raise SystemExit(
            f"header/matrix mismatch: {len(names)} names vs {n_val} value "
            f"columns in {path} — refusing to guess the sample mapping"
        )
    if len(set(samples)) != len(samples):
        raise SystemExit(f"duplicate sample columns in {path}")
    if n_bad:
        print(f"  [warn] {n_bad} unparseable data rows skipped in {path.name}")
    if not all(s.startswith("RNA") for s in samples):
        raise SystemExit(f"unexpected sample column ids: {samples[:5]}")
    return samples, gene_ids, mat


def cpm_log1p_z(mat: np.ndarray) -> np.ndarray:
    cpm = mat / np.maximum(mat.sum(axis=0, keepdims=True), 1.0) * 1e6
    t = np.log1p(cpm)
    return t


def top_mad_genes(t: np.ndarray, gene_ids: list[str], n: int = PANEL_N):
    mad = np.median(np.abs(t - np.median(t, axis=1, keepdims=True)), axis=1)
    idx = np.argsort(mad)[::-1][:n]
    return [gene_ids[i] for i in idx], idx


def zscore_panel(t: np.ndarray, idx, mu=None, sd=None) -> np.ndarray:
    sub = t[idx]  # panel genes x samples
    if mu is None:
        mu = sub.mean(axis=1, keepdims=True)
    if sd is None:
        sd = np.maximum(sub.std(axis=1, keepdims=True), 1e-12)
    return (sub - mu) / sd


def cohen_kappa(a: list, b: list) -> float:
    labels = sorted(set(a) | set(b))
    n = len(a)
    o = sum(1 for x, y in zip(a, b) if x == y) / n
    e = sum(
        (sum(1 for x in a if x == l) / n) * (sum(1 for y in b if y == l) / n)
        for l in labels
    )
    return (o - e) / (1 - e) if e < 1 else 1.0


def read_ann(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def build_items(samples, gene_ids, t, ann_map, mode, panel=None, z=None):
    if panel is None:
        panel, pidx = top_mad_genes(t, gene_ids)
        z = zscore_panel(t, pidx)
    else:
        z = z  # panel + z precomputed by the caller (shared variant prompts)
    items = []
    for j, sid in enumerate(samples):
        meta = ann_map[sid]
        fib = int(meta["fib"])
        genes_txt = ", ".join(f"{panel[i]}={z[i, j]:.2f}" for i in range(len(panel)))
        verb = VERBALIZATIONS[zlib.crc32(sid.encode()) % len(VERBALIZATIONS)]
        for task in sorted(TASK_HEADERS):
            if mode == "anchor":
                out_task = task
            elif mode == "ext":
                out_task = EXT_TASKS[task]
            else:
                out_task = AMC_TASKS[task]
            if task.endswith("01"):
                ans = "yes" if fib >= 3 else "no"
            elif task.endswith("02"):
                ans = f"F{fib}"
            else:
                ans = str(fib)
            rec = dict(
                task=out_task,
                split="test",
                sample=sid,
                source="S-BSST1614",
                prompt=verb + TASK_HEADERS[task].format(genes=genes_txt),
                answer=ans,
                label_source=meta["label_source"],
            )
            if meta.get("bps_brunt") is not None:
                rec["bps_brunt"] = meta["bps_brunt"]
            if mode in ("anchor", "amcvar"):
                rec["nafld_dx"] = meta["nafld_dx"]
                rec["reader_agreement"] = meta["agreement"]
            items.append(rec)
    return items


def write_corpus(path: Path, items: list[dict], meta: dict):
    with gzip.open(path, "wt") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in items:
            f.write(json.dumps(r) + "\n")
    print(f"  -> {path.name}: {len(items)} items")


def update_manifest(counts: dict[str, int], sha_sources: dict[str, str], corpus_shas: dict[str, str], notes: list[str]):
    if not MANIFEST.exists():
        raise SystemExit(f"MANIFEST not found at {MANIFEST}")
    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-17"
    m["rules"].append(
        "MB-89xx: S-BSST1614 plasma cfRNA fibrosis family (freeze-17): 89xx = cohort 1 "
        "test (112 samples, biopsy Brunt 0-4 UZA gold, AMC second reader, kappa in meta); "
        "891x = cohort 2 NAFLD-etiology external holdout (one sample per Subject_ID, "
        "clinical-consensus F0-F4 gold with bps_brunt flag); 8901/8911 advanced-fibrosis "
        "binary, 8902/8912 f_stage 5-class, 8905/8915 ordinal 0-4; panel top-200 MAD "
        "internal per corpus; CPM->log1p->per-sample z; TEST-ONLY, never train-side"
        + (notes[0] if notes and notes[0] else "")
    )
    for k, v in counts.items():
        m["counts"][k] = v
    m["sources_sha16"] = sha_sources
    m["corpus_sha16"] = corpus_shas
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"  manifest -> {MANIFEST} (v3-freeze-17)")


def main():
    if not DATA.exists():
        raise SystemExit(f"data dir missing: {DATA} (see download commands in docstring)")
    c1 = DATA / "htseq_cohort1.txt"
    c2 = DATA / "htseq_cohort2.txt"
    a1 = DATA / "annotation_cohort1.csv"
    a2 = DATA / "annotation_cohort2.csv"
    for p in (c1, c2, a1, a2):
        if not p.exists():
            raise SystemExit(f"missing source: {p}")

    print("== load cohort 1 ==")
    s1, g1, m1 = load_matrix(c1)
    ann1 = read_ann(a1)
    ids1 = {r["SMAPLE_RNA"] for r in ann1}
    ok1 = set(s1) & ids1
    extra1 = set(s1) - ids1
    missing1 = ids1 - set(s1)
    print(f"  matrix cols {len(s1)} | annotated {len(ids1)} | joined {len(ok1)} | "
          f"unannotated cols {sorted(extra1)} | unmatched ann ids {len(missing1)}")
    if len(missing1):
        raise SystemExit(f"annotation ids absent from matrix: {sorted(missing1)[:5]}")
    keep1 = [s for s in s1 if s in ok1]  # drops unannotated columns (RNA015845)

    fib_map1 = {r["SMAPLE_RNA"]: r for r in ann1}
    for r in ann1:
        if r["fibrosis"] not in {"0", "1", "2", "3", "4"}:
            raise SystemExit(f"cohort1 fibrosis out of range: {r['SMAPLE_RNA']} {r['fibrosis']}")
    kappa = cohen_kappa([fib_map1[s]["fibrosis"] for s in keep1],
                        [fib_map1[s]["fibrosis_AMC"] for s in keep1])
    print(f"  UZA vs AMC kappa: {kappa:.3f}")
    # Amendment 2026-10-29 (Option C, human decision; plan §13, RUNLOG entry):
    # the frozen kappa<0.6 concordant-only fallback is LIFTED. The anchor
    # keeps all 112 samples with UZA gold; an AMC-gold variant pair
    # (MB-8921/8922/8925, same prompt strings) is emitted on the samples
    # where AMC staged (AMC-NA excluded); per-item reader_agreement flag
    # preserved for the concordant-56 sensitivity.
    keep1_amc = [s for s in keep1
                 if fib_map1[s]["fibrosis_AMC"] in {"0", "1", "2", "3", "4"}]
    print(f"  [amendment C] UZA anchor all {len(keep1)}; AMC-gold variants on "
          f"{len(keep1_amc)} (AMC-NA excluded)")

    idx1 = [s1.index(s) for s in keep1]
    t1 = cpm_log1p_z(m1[:, idx1])
    ann_map1 = {
        s: dict(fib=fib_map1[s]["fibrosis"], label_source="biopsy_brunt_uza",
                nafld_dx=fib_map1[s].get("NAFLD_Diagnosis", ""),
                amc_fib=fib_map1[s]["fibrosis_AMC"],
                agreement=("concordant" if fib_map1[s]["fibrosis"] == fib_map1[s]["fibrosis_AMC"]
                           else "discordant"))
        for s in keep1
    }
    panel1, pidx1 = top_mad_genes(t1, g1)
    z1 = zscore_panel(t1, pidx1)
    items1 = build_items(keep1, g1, t1, ann_map1, "anchor", panel=panel1, z=z1)

    # Option C AMC-gold variant pair: same panel, same gene moments (frozen on
    # the 112-sample anchor) and therefore byte-identical prompt strings for
    # the shared samples; only the gold differs.
    idx_amc = [s1.index(s) for s in keep1_amc]
    t1_amc = cpm_log1p_z(m1[:, idx_amc])
    mu1 = t1[pidx1].mean(axis=1, keepdims=True)
    sd1 = np.maximum(t1[pidx1].std(axis=1, keepdims=True), 1e-12)
    z_amc = zscore_panel(t1_amc, pidx1, mu=mu1, sd=sd1)
    ann_map_amc = {
        s: dict(fib=ann_map1[s]["amc_fib"], label_source="biopsy_brunt_amc",
                nafld_dx=ann_map1[s]["nafld_dx"], agreement=ann_map1[s]["agreement"])
        for s in keep1_amc
    }
    items_amc = build_items(keep1_amc, g1, t1_amc, ann_map_amc, "amcvar",
                            panel=panel1, z=z_amc)

    print("== load cohort 2 ==")
    s2, g2, m2 = load_matrix(c2)
    ann2 = read_ann(a2)
    ids2 = {r["SMAPLE_RNA"] for r in ann2}
    ok2 = set(s2) & ids2
    print(f"  matrix cols {len(s2)} | annotated {len(ids2)} | joined {len(ok2)} | "
          f"unmatched ann ids {len(ids2 - set(s2))}")
    if ids2 - set(s2):
        raise SystemExit("cohort2 annotation ids absent from matrix")

    sub = [r for r in ann2 if r.get("Etiology") in NAFLD_ETIOLOGIES]
    by_subj: dict[str, list] = {}
    for r in sub:
        by_subj.setdefault(r["Subject_ID"], []).append(r)
    kept2 = []
    for sid, rs in by_subj.items():
        base = [r for r in rs if r.get("Visit_Type") == "Baseline"]
        pick = (base or rs)[0]
        kept2.append(pick)
    kept2 = [r for r in kept2 if r.get("Fibrosis") in F_STAGES]
    print(f"  NAFLD-etiology subset {len(sub)} samples -> {len(by_subj)} subjects -> "
          f"{len(kept2)} labeled samples")

    if kept2:
        run_table = Counter((r["Fibrosis"], r.get("Sequencing_run", "")) for r in kept2)
        runs = sorted({run for _, run in run_table})
        fibs = sorted(F_STAGES)
        tab = [[run_table.get((f, r), 0) for r in runs] for f in fibs]
        try:
            chi2, p, _, _ = chi2_contingency(tab)
            print(f"  Fibrosis x Sequencing_run: chi2={chi2:.1f} p={p:.3g}")
        except ValueError:
            print("  [warn] chi2 skipped (sparse table)")
        batch_flag = "batch-confounded" if locals().get("p", 1) < 0.05 else "clean"

    s2_sel = [r["SMAPLE_RNA"] for r in kept2]
    idx2 = [s2.index(s) for s in s2_sel]
    t2 = cpm_log1p_z(m2[:, idx2])
    ann_map2 = {}
    for r in kept2:
        bps = r.get("BPS_fibrosisBrunt", "").strip()
        ann_map2[r["SMAPLE_RNA"]] = dict(
            fib=str(F_STAGES[r["Fibrosis"]]), label_source="clinical_consensus",
            bps_brunt=int(bps) if bps.isdigit() else None)
    items2 = build_items(s2_sel, g2, t2, ann_map2, "ext")

    sha_sources = {p.name: sha16(p) for p in (c1, c2, a1, a2)}
    out1 = PROMPTS / "MB-89xx_plasmacf_test.jsonl.gz"
    out2 = PROMPTS / "MB-89xx_plasmacf_ext_test.jsonl.gz"
    out3 = PROMPTS / "MB-89xx_plasmacf_amcvar_test.jsonl.gz"
    meta1 = dict(n_records=len(items1), seed=SEED, built="2026-10-29",
                 builder="S-BSST1614 plasma cfRNA biopsy-anchored test",
                 join="112/112", uza_amc_kappa=round(kappa, 3),
                 amendment="Option C (2026-10-29): UZA anchor all 112, kappa fallback lifted",
                 fibrosis_counts=dict(Counter(a["fib"] for a in ann_map1.values())),
                 sources=sha_sources)
    meta_amc = dict(n_records=len(items_amc), seed=SEED, built="2026-10-29",
                    builder="S-BSST1614 plasma cfRNA AMC-gold variant pair (Option C)",
                    join="112/112 -> AMC-staged subset", uza_amc_kappa=round(kappa, 3),
                    note="prompt strings identical to the 89xx anchor items for shared samples",
                    fibrosis_counts=dict(Counter(a["fib"] for a in ann_map_amc.values())),
                    sources=sha_sources)
    meta2 = dict(n_records=len(items2), seed=SEED, built="2026-10-29",
                 builder="S-BSST1614 plasma cfRNA external holdout",
                 join="821/821 -> NAFLD-etiology dedupe", batch_flag=batch_flag,
                 fibrosis_counts=dict(Counter(a["fib"] for a in ann_map2.values())),
                 bps_subpanel=sum(1 for a in ann_map2.values() if a["bps_brunt"] is not None),
                 sources=sha_sources)
    write_corpus(out1, items1, meta1)
    write_corpus(out2, items2, meta2)
    write_corpus(out3, items_amc, meta_amc)
    rule_extra = (
        "; 2026-10-29 execution (Option C, human decision, RUNLOG): kappa=%.3f -> "
        "UZA anchor kept on all 112 with per-item reader_agreement flag; AMC-gold "
        "variant pair MB-8921/8922/8925 emitted on the %d AMC-staged samples with "
        "prompt strings identical to the 89xx anchor items (label-noise control)"
        % (kappa, len(keep1_amc))
    )
    update_manifest({out1.name: len(items1), out2.name: len(items2), out3.name: len(items_amc)},
                    sha_sources,
                    {out1.name: sha16(out1), out2.name: sha16(out2), out3.name: sha16(out3)},
                    [rule_extra])
    print("done.")


if __name__ == "__main__":
    main()
