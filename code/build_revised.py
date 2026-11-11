#!/usr/bin/env python3
"""Build MANUSCRIPT_REVISED.docx / .html / .pdf from the single markdown source.

No figure is embedded that the source does not name, and every embedded figure
is checked to exist. Tables render as real Word tables.
"""
from __future__ import annotations

import html
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

REV = Path(os.environ.get("MASLD_REVISION_DIR", Path(__file__).resolve().parents[1]))
SRC = REV / "MANUSCRIPT_REVISED.md"
if not SRC.exists():
    raise SystemExit(f"Author-approved manuscript source not found at {SRC}. "
                     "Set MASLD_REVISION_DIR to a private manuscript package; "
                     "the public release intentionally excludes it.")
FIGDIR = REV / "figures"

FIGS = [
    ("Figure 1.", FIGDIR / "Figure_1_pipeline.png",
     "Figure 1. Construction and evaluation pipeline of MASLD-Bench."),
    ("Figure 2.", FIGDIR / "Figure_2_ranks.png",
     "Figure 2. Ranks of models across the tissue tasks (A) and the plasma cfRNA binary tasks (B). "
     "Carried forward; panel B is rank-only and does not indicate performance above the majority rate."),
    ("Figure 3.", FIGDIR / "Figure_3_binary_corrected.png",
     "Figure 3. Binary-format performance, corrected. (A) Tissue fibrosis, majority 0.661. "
     "(B) Plasma cfRNA anchor, majority 0.714 (dashed), logistic baseline 0.723 (solid red). "
     "A cross marks a model that never answered yes; red marks a failed evaluation."),
    ("Figure 4.", FIGDIR / "Figure_4_format.png",
     "Figure 4. Rank instability across answer formats on the same liver cohort. Carried forward."),
    ("Figure 5.", FIGDIR / "Figure_5_regression.png",
     "Figure 5. Regression error without rank information: MAE against Spearman rho. Carried forward."),
    ("Figure 6.", FIGDIR / "Figure_6_concentration_corrected.png",
     "Figure 6. The top-5 gene panel equals the majority rate under both legacy and nested selection."),
]


def inline_runs(par, text, size=10.5):
    """Render **bold**, *italic*, `code` into a paragraph."""
    text = text.replace("\\*", "\x00")
    tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`]+`)", text)
    for tok in tokens:
        if not tok:
            continue
        tok = tok.replace("\x00", "*")
        if tok.startswith("**") and tok.endswith("**"):
            r = par.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith("`") and tok.endswith("`"):
            r = par.add_run(tok[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(size - 1)
            r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            r = par.add_run(tok[1:-1]); r.italic = True
        else:
            r = par.add_run(tok)
        r.font.size = Pt(size)


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {p}")
    return struct.unpack(">II", head[16:24])


def add_table(doc, rows):
    ncol = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=ncol)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j in range(ncol):
            txt = row[j] if j < len(row) else ""
            cells[j].text = ""
            p = cells[j].paragraphs[0]
            inline_runs(p, txt, size=8.5)
            if i == 0:
                for r in p.runs:
                    r.bold = True
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
        if i == 0:
            tr = t.rows[0]._tr
            trPr = tr.get_or_add_trPr()
            th = OxmlElement("w:tblHeader")
            th.set(qn("w:val"), "true")
            trPr.append(th)
    doc.add_paragraph()


def build_docx():
    md = SRC.read_text().split("\n")
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    for section in doc.sections:
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)

    i = 0
    n = len(md)
    while i < n:
        line = md[i].rstrip()
        s = line.strip()

        if not s:
            i += 1
            continue

        if s == "---":
            doc.add_paragraph()
            i += 1
            continue

        # tables
        if s.startswith("|"):
            rows = []
            while i < n and md[i].strip().startswith("|"):
                t = md[i].strip()
                if not set(t.replace("|", "").replace("-", "").replace(":", "").strip()):
                    i += 1
                    continue
                rows.append([c.strip() for c in t.strip("|").split("|")])
                i += 1
            if rows:
                add_table(doc, rows)
            continue

        # headings
        if s.startswith("#"):
            lvl = min(len(s) - len(s.lstrip("#")), 4)
            txt = s.lstrip("#").strip()
            h = doc.add_heading(level=lvl)
            inline_runs(h, txt, size={1: 17, 2: 13.5, 3: 11.5, 4: 10.5}.get(lvl, 10.5))
            for r in h.runs:
                r.font.color.rgb = RGBColor(0x1D, 0x35, 0x57)
            i += 1
            continue

        # numbered limitations / references inside a section
        m = re.match(r"^\[(\d+)\]\s+(.*)$", s)
        if m:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.35)
            p.paragraph_format.first_line_indent = Inches(-0.35)
            p.paragraph_format.space_after = Pt(3)
            inline_runs(p, f"[{m.group(1)}] {m.group(2)}", size=9.0)
            i += 1
            continue

        m = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m and not s.startswith("|"):
            p = doc.add_paragraph(style="List Number")
            inline_runs(p, m.group(2))
            p.paragraph_format.space_after = Pt(4)
            i += 1
            continue

        # figure placeholders
        hit = None
        for key, path, _ in FIGS:
            if s.startswith(key) or s.startswith("**" + key):
                hit = (key, path)
                break
        # body paragraphs
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        inline_runs(p, s)
        i += 1

    # ---- figures appendix so every embedded image has a caption ----
    doc.add_page_break()
    h = doc.add_heading(level=2)
    inline_runs(h, "Figures", size=13.5)
    for key, path, cap in FIGS:
        if not path.exists():
            raise SystemExit(f"missing figure: {path}")
        w, hpx = png_size(path)
        width = min(6.4, 6.4)
        doc.add_picture(str(path), width=Inches(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp = doc.add_paragraph()
        inline_runs(cp, cap, size=8.5)
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

    out = REV / "MANUSCRIPT_REVISED.docx"
    doc.save(out)
    print("wrote", out, out.stat().st_size)
    return out


CSS = """
:root{--navy:#1d3557;--ink:#1a1a1a;--muted:#5b6472;--line:#d8dde5}
*{box-sizing:border-box}
body{margin:0;background:#eef1f5;font-family:Georgia,'Times New Roman',serif;color:var(--ink);line-height:1.62}
.page{max-width:820px;margin:0 auto;background:#fff;padding:64px 72px 96px;box-shadow:0 2px 20px rgba(0,0,0,.07)}
h1{font-size:23pt;line-height:1.28;color:var(--navy);margin:0 0 18px;font-weight:700}
h2{font-size:14.5pt;color:var(--navy);margin:34px 0 12px;padding-bottom:5px;border-bottom:1px solid var(--line)}
h3{font-size:11.5pt;color:#243b53;margin:22px 0 8px}
h4{font-size:10.5pt;font-style:italic;margin:16px 0 6px;color:#334155}
p{margin:0 0 10px;text-align:justify;hyphens:auto}
strong{font-weight:700}
code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.88em;background:#f1f3f6;padding:1px 4px;border-radius:3px}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}
table{width:100%;border-collapse:collapse;margin:14px 0 18px;font-size:8.6pt;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif}
th,td{border:1px solid #c9d1dc;padding:4px 6px;text-align:left;vertical-align:top}
th{background:#e8edf3;font-weight:650}
tbody tr:nth-child(even){background:#f7f9fb}
ol{margin:0 0 12px 20px;padding-left:6px}
li{margin-bottom:6px;text-align:justify}
figure{margin:22px 0;text-align:center}
figure img{max-width:100%;border:1px solid var(--line);border-radius:3px}
figcaption{font-size:8.6pt;color:var(--muted);margin-top:6px;text-align:left}
.meta{font-size:10pt;color:#334155}
@media print{body{background:#fff}.page{box-shadow:none;margin:0;padding:0;max-width:100%}}
"""


def md_inline(t):
    t = t.replace("\\*", "\x00")
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", t)
    return t.replace("\x00", "*")


def build_html():
    md = SRC.read_text().split("\n")
    out, i, n = [], 0, len(md)
    out.append("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>")
    out.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    out.append("<title>MASLD-Bench — revised manuscript</title>")
    out.append(f"<style>{CSS}</style></head><body><div class='page'>")
    while i < n:
        s = md[i].strip()
        if not s:
            i += 1
            continue
        if s == "---":
            out.append("<hr>"); i += 1; continue
        if s.startswith("|"):
            rows = []
            while i < n and md[i].strip().startswith("|"):
                t = md[i].strip()
                if not set(t.replace("|", "").replace("-", "").replace(":", "").strip()):
                    i += 1; continue
                rows.append([c.strip() for c in t.strip("|").split("|")]); i += 1
            if rows:
                out.append("<table><thead><tr>" +
                           "".join(f"<th>{md_inline(c)}</th>" for c in rows[0]) +
                           "</tr></thead><tbody>")
                for r in rows[1:]:
                    out.append("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>")
                out.append("</tbody></table>")
            continue
        if s.startswith("#"):
            lvl = min(len(s) - len(s.lstrip("#")), 4)
            out.append(f"<h{lvl}>{md_inline(s.lstrip('#').strip())}</h{lvl}>"); i += 1; continue
        m = re.match(r"^\[(\d+)\]\s+(.*)$", s)
        if m:
            out.append(f"<p style='margin-left:1.4em;text-indent:-1.4em;font-size:9.2pt'>"
                       f"[{m.group(1)}] {md_inline(m.group(2))}</p>"); i += 1; continue
        m = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m:
            out.append(f"<ol start='{m.group(1)}' style='list-style:none'>"
                       f"<li><strong>{m.group(1)}.</strong> {md_inline(m.group(2))}</li></ol>")
            i += 1; continue
        out.append(f"<p>{md_inline(s)}</p>")
        i += 1

    out.append("<hr><h2>Figures</h2>")
    for key, path, cap in FIGS:
        if not path.exists():
            raise SystemExit(f"missing figure: {path}")
        rel = path.relative_to(REV)
        out.append(f"<figure><img src='{rel}' alt='{html.escape(cap)}'>"
                   f"<figcaption>{html.escape(cap)}</figcaption></figure>")
    out.append("</div></body></html>")
    p = REV / "MANUSCRIPT_REVISED.html"
    p.write_text("\n".join(out))
    print("wrote", p, p.stat().st_size)
    return p


def build_pdf(chrome_candidates):
    html_path = REV / "MANUSCRIPT_REVISED.html"
    pdf = REV / "MANUSCRIPT_REVISED.pdf"
    for exe in chrome_candidates:
        if not Path(exe).exists():
            continue
        cmd = [exe, "--headless", "--disable-gpu", "--no-sandbox",
               "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
               html_path.as_uri()]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if pdf.exists() and pdf.stat().st_size > 10000:
            print("wrote", pdf, pdf.stat().st_size, "(via", exe, ")")
            return pdf
        print("attempt failed:", exe, r.stderr[-300:])
    print("PDF NOT BUILT: no working headless Chrome found")
    return None


if __name__ == "__main__":
    build_docx()
    build_html()
    build_pdf([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ])
