import os, json, time, pathlib
import pandas as pd
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
PROC = ROOT / os.getenv('PROCESSED_DIR', 'data/processed')
REPORTS = ROOT / os.getenv('REPORTS_DIR', 'reports')
REPORTS.mkdir(parents=True, exist_ok=True)

def write_provenance(state, source, hint=None):
    prov = {"synthetic": False if state=="real" else None, "source": source, "ts": int(time.time())}
    if hint: prov["hint"] = hint
    with open(ROOT/"data_provenance.json","w") as f: json.dump(prov, f, indent=2)

def main():
    vids = pd.read_parquet(PROC/"videos.parquet")
    # Try Analytics per-video
    ana_path = PROC/"analytics_365d.parquet"
    analytics = None
    if ana_path.exists():
        analytics = pd.read_parquet(ana_path)
        if "video" in analytics.columns and "videoId" not in analytics.columns:
            analytics = analytics.rename(columns={"video":"videoId"})
        if "videoId" not in analytics.columns or analytics["videoId"].nunique()==0:
            analytics = None

    # Fallback: Data API stats
    dataapi_stats = None
    stats_path = PROC/"dataapi_video_stats.parquet"
    if stats_path.exists():
        dataapi_stats = pd.read_parquet(stats_path)

    # Select best available
    if analytics is not None:
        out = vids.merge(analytics, on="videoId", how="left")
        write_provenance("real","analytics_per_video")
    elif dataapi_stats is not None:
        out = vids.merge(dataapi_stats, on="videoId", how="left")
        write_provenance("real","dataapi_video_stats","analytics_per_video_unavailable")
    else:
        # nothing per-video available — keep videos only (HONEST MODE)
        out = vids.copy()
        write_provenance("partial","videos_only","no_per_video_metrics")
    out.to_parquet(PROC/"master_join.parquet", index=False)
    print("Wrote ->", PROC/"master_join.parquet", "rows:", len(out))

if __name__ == "__main__":
    main()
