# masld-benchmarks-site

Static site for **MASLD-Bench** — the disease-specific, histology-grounded
omics-LLM benchmark. No build step: plain HTML/CSS/JS that renders
`assets/leaderboard.json`, which is exported from the benchmark's
`results/leaderboard.csv` (297 rows, freeze v3-freeze-17).

## Local preview

Open `index.html` in a browser. The leaderboard fetches
`assets/leaderboard.json` — if your browser blocks `fetch` on `file://`,
run a one-line server:

    python3 -m http.server 8000

then open http://localhost:8000

## Deploy (pick one)

- **GitHub Pages** — push this folder to a repo, enable Pages on `main`.
- **Netlify / Cloudflare Pages** — drag the folder in, or connect the repo.
- **Hugging Face Spaces** — create a static Space, upload these files.
  (This also becomes the natural home for the MASLD-claw Tier-2 chat app.)

Then point the domain at the host:

    masldbenchmarks.org  →  CNAME to the Pages/Netlify/Spaces URL

## Before going live (checklist)

1. Preprint posted (bioRxiv / medRxiv) — link it on `index.html`.
2. HF model repos public — replace the "publishing…" placeholders on
   `models.html` with real links.
3. Replace `assets/leaderboard.json` with a fresh export whenever the
   leaderboard grows (the export script lives in the benchmark repo).
4. Confirm the disclaimer footer stays on every page.

## Refresh the leaderboard data

    MASLD_LLM_ROOT="…/My Drive/masld-llm" python3 export_site_json.py
