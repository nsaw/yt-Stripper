
import os
import pathlib
import datetime as dt
import pandas as pd
from dotenv import load_dotenv
from auth import yta_service

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
PROC = ROOT / os.getenv('PROCESSED_DIR', 'data/processed')
CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')

# Per-video report: detailed metrics with video dimension (last 365d)
def run_report(yta, start_date, end_date):  # strict hybrid
    try:
        # Per-video metrics with video dimension (using only supported metrics)
        metrics = 'views,estimatedMinutesWatched,averageViewDuration'
        dims = 'video'
        resp = yta.reports().query(
            ids='channel==MINE',
            startDate=start_date, endDate=end_date,
            metrics=metrics,
            dimensions=dims,
            maxResults=1000,
            startIndex=1
        ).execute()
        cols = resp.get('columnHeaders', [])
        colnames = [c['name'] for c in cols]
        rows = resp.get('rows', [])
        import pandas as pd
        out = pd.DataFrame(rows, columns=colnames)
        if out.empty:
            raise RuntimeError("Analytics API returned no rows (per-video). Check owner OAuth/scopes/quota.")
        return out
    except Exception as e:
        print(f"Analytics API error: {e}")
        return None

if __name__ == "__main__":
    try:
        yta = yta_service()
        end = dt.date.today()
        start = end - dt.timedelta(days=365)
        df = run_report(yta, start.isoformat(), end.isoformat())
        if df is not None and not df.empty:
            df.rename(columns={'video':'videoId'}, inplace=True)
            df.to_parquet(PROC / 'analytics_365d.parquet', index=False)
            print("Saved analytics ->", PROC / 'analytics_365d.parquet')
        else:
            print("No analytics data available. API quota exceeded or authentication failed.")
            raise RuntimeError("Analytics API returned no data. Check quota and authentication.")
    except Exception as e:
        print(f"Analytics API access failed: {e}")
        raise RuntimeError(f"Analytics API failed: {e}")
