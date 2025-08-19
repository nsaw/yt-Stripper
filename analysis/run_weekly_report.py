import os, json, pathlib, pandas as pd
from dotenv import load_dotenv
from insight_engine import generate_insights_and_actions, write_reports

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
PROC = ROOT / os.getenv('PROCESSED_DIR','data/processed')
REPORTS = ROOT / os.getenv('REPORTS_DIR','reports')

def main():
    mp = PROC/'master_join.parquet'
    prov_p = ROOT/'data_provenance.json'
    if not mp.exists():
        raise SystemExit('master_join.parquet missing – run the pipeline first.')
    df = pd.read_parquet(mp)
    prov = {}
    if prov_p.exists():
        prov = json.load(open(prov_p))
    payload = generate_insights_and_actions(df, prov)
    write_reports(payload, str(REPORTS))
    print('✅ Wrote insights.md and actions.csv in', REPORTS)

if __name__ == "__main__":
    main()
