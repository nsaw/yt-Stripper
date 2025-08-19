
# YouTube Deep-Dive Audit (Starter)

End-to-end pipeline to pull your channel's YouTube Analytics + Data API, captions, comments, thumbnails, then run cross-analyses:
- **Scripts vs Titles** (semantic + structural alignment)
- **Retention vs Timecodes/VO** (where people drop)
- **Thumbnail visual analysis** (contrast, text density, faces, saliency)
- **Comment topics vs performance**
- **Competitive benchmark** (similar channels in your vertical)

> This is a scaffold with working fetchers and analysis stubs. Fill in TODOs as you connect OAuth and refine metrics.

## Quick Start

1. **Python 3.10+** recommended.
2. `pip install -r requirements.txt`
3. Create Google Cloud OAuth credentials (Desktop) and download `client_secret.json` to the repo root.
4. Copy `.env.example` → `.env` and set your values.
5. First run will open a browser for OAuth consent.

### Pull data
```bash
python scripts/fetch_videos.py
python scripts/fetch_analytics.py
python scripts/fetch_comments.py
python scripts/fetch_captions.py
```

### Run analysis
```bash
python analysis/cross_analyze.py
python analysis/thumbnail_scores.py
```

Artifacts land in `data/processed/` (DuckDB/Parquet/CSVs) and `reports/`.

## What this project does

- **Data ingestion**
  - YouTube **Data API v3** → videos, metadata, thumbnails, comments, captions list & download
  - **YouTube Analytics API** → views, watch time, impressions, CTR, avg view duration, subscribers gained, traffic sources
- **Model-free insights (fast)**
  - CTR vs title patterns
  - Retention vs VO/script beats (via caption timestamps)
  - Thumbnail feature heuristics: brightness/contrast/sharpness/text-density (OCR), face count (optional), saliency
  - Comment topic clustering (lightweight, local embeddings), toxicity/positivity heuristic
- **LLM-enhanced insights (optional)**
  - Local LLM for script/VO critique (recommended for cost/privacy)
  - Cloud model for vision if you want deeper thumbnail reads (optional)

## Local vs Cloud LLM

- **Local GPT-style model (recommended for bulk parsing):**
  - Good: privacy, cost-control, batch throughput
  - Use: Llama 3.x or Mixtral + `llama-cpp-python` / vLLM for text; `clip`/`blip` for basic vision
- **Cloud (OpenAI, Anthropic) for vision & high-accuracy summaries** (optional):
  - Good: best-in-class reasoning/vision
  - Use selectively on *shortlisted* videos/thumbnails after first-pass filters

## GH Actions

A workflow is included for nightly pulls + analysis on your private repo. It caches auth tokens as artifacts (optional). Lock down secrets.

## Competitive set

`analysis/cross_analyze.py` includes a simple search-based approach to pick 5–10 similar channels and compare public metrics.

## Notes

- Audience retention *per second* requires the Analytics API and may be sampled/limited. We approximate retention-beat mapping using caption timestamps + avg view duration + relative watch at time t (where available). Fill the TODO to expand this if your account has advanced report access.
- Thumbnail OCR uses Tesseract if installed; otherwise it skips text-density metrics gracefully.

