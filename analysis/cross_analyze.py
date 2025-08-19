
import os
import pathlib
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
PROC = ROOT / os.getenv('PROCESSED_DIR', 'data/processed')
REPORTS = ROOT / os.getenv('REPORTS_DIR', 'reports')
REPORTS.mkdir(parents=True, exist_ok=True)

def load_data():
    # Prefer unified master_join if available
    import os
    mp = PROC / 'master_join.parquet'
    if mp.exists():
        df = pd.read_parquet(mp)
        comments = None
        try:
            comments = pd.read_parquet(PROC / 'comments.parquet')
        except Exception: comments = pd.DataFrame(columns=['videoId','text'])
        return df, comments
    
    # Fallback to manual merge
    vids = pd.read_parquet(PROC / 'videos.parquet')
    analytics = pd.read_parquet(PROC / 'analytics_365d.parquet')
    if 'videoId' in analytics.columns:
        df = vids.merge(analytics, on='videoId', how='left')
    else:
        df = vids.copy()  # analytics missing per-video; proceed with vids only
    comments = None
    try:
        comments = pd.read_parquet(PROC / 'comments.parquet')
    except Exception:
        comments = pd.DataFrame(columns=['videoId','text'])
    return df, comments

def srt_to_segments(srt_path):
    # very simple srt parser
    segs = []
    if not srt_path or not os.path.exists(srt_path):
        return segs
    with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
        block = []
        for line in f:
            line=line.strip()
            if not line:
                if block:
                    try:
                        # block: [idx, time, text...]
                        times = block[1]
                        text = ' '.join(block[2:])
                        start = times.split('-->')[0].strip()
                        h,m,s = start.split(':')
                        t = int(float(h))*3600 + int(m)*60 + float(s.replace(',','.'))
                        segs.append((t, text))
                    except Exception:
                        pass
                    block = []
            else:
                block.append(line)
    return segs

def main():
    df, comments = load_data()
    # Embedding model (local, CPU-friendly)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    # Title ↔ caption alignment score (cosine sim)
    cap_index = pd.read_parquet(PROC / 'captions_index.parquet') if (PROC / 'captions_index.parquet').exists() else pd.DataFrame()
    title_scores = []
    for _, row in df.iterrows():
        title = row.get('title','') or ''
        vid = row['videoId']
        segs = []
        cap_row = cap_index[cap_index['videoId']==vid].head(1)
        if not cap_row.empty and isinstance(cap_row.iloc[0]['file'], str):
            segs = srt_to_segments(cap_row.iloc[0]['file'])
        cap_text = ' '.join([t for _, t in segs])[:5000]
        if title and cap_text:
            emb = model.encode([title, cap_text], convert_to_tensor=True)
            sim = float(util.cos_sim(emb[0], emb[1]).cpu().numpy())
        else:
            sim = np.nan
        title_scores.append({'videoId': vid, 'title_caption_sim': sim})
    simdf = pd.DataFrame(title_scores)
    out = df.merge(simdf, on='videoId', how='left')
    # Correlate with CTR and avg view duration
    cols = [c for c in ['clickThroughRate','averageViewDuration','title_caption_sim'] if c in out.columns]
    corr = out[cols].corr(numeric_only=True) if cols else pd.DataFrame()
    corr.to_csv(REPORTS / 'correlations.csv')
    out.to_parquet(PROC / 'master_join.parquet', index=False)
    print('Wrote:', REPORTS / 'correlations.csv', 'and', PROC / 'master_join.parquet')

if __name__ == '__main__':
    main()
