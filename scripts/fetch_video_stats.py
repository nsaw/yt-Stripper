import os, time, pathlib
import pandas as pd
from dotenv import load_dotenv
from auth import yt_service

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
PROC = ROOT / os.getenv('PROCESSED_DIR', 'data/processed')

BATCH=50
SLEEP=0.6  # gentle backoff

def main():
    yt = yt_service()
    vids = pd.read_parquet(PROC / 'videos.parquet')
    ids = vids['videoId'].dropna().unique().tolist()
    rows = []
    for i in range(0, len(ids), BATCH):
        sub = ids[i:i+BATCH]
        resp = yt.videos().list(part="statistics", id=",".join(sub)).execute()
        for it in resp.get("items", []):
            st = it.get("statistics", {})
            rows.append({
                "videoId": it["id"],
                "viewCount": int(st.get("viewCount", 0)) if st.get("viewCount") else None,
                "likeCount": int(st.get("likeCount", 0)) if st.get("likeCount") else None,
                "commentCount": int(st.get("commentCount", 0)) if st.get("commentCount") else None,
            })
        time.sleep(SLEEP)
    out = pd.DataFrame(rows)
    out.to_parquet(PROC / "dataapi_video_stats.parquet", index=False)
    print("Saved ->", PROC / "dataapi_video_stats.parquet", "rows:", len(out))

if __name__ == "__main__":
    main()
