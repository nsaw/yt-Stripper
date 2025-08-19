
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

# Basic report: per-video core metrics (last 365d)
def run_report(yta, start_date, end_date):
    metrics = 'views,estimatedMinutesWatched,averageViewDuration'
    dims = 'video'
    resp = yta.reports().query(
        ids='channel==MINE',
        startDate=start_date, endDate=end_date,
        metrics=metrics,
        dimensions=dims,
        maxResults=1000
    ).execute()
    cols = resp.get('columnHeaders', [])
    colnames = [c['name'] for c in cols]
    rows = resp.get('rows', [])
    return pd.DataFrame(rows, columns=colnames)

if __name__ == "__main__":
    yta = yta_service()
    end = dt.date.today()
    start = end - dt.timedelta(days=365)
    df = run_report(yta, start.isoformat(), end.isoformat())
    df.rename(columns={'video':'videoId'}, inplace=True)
    df.to_parquet(PROC / 'analytics_365d.parquet', index=False)
    print("Saved analytics ->", PROC / 'analytics_365d.parquet')
