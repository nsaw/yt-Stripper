
import os
import pathlib
import pandas as pd
from dotenv import load_dotenv
from auth import yt_service

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
RAW = ROOT / os.getenv('RAW_DIR', 'data/raw')
PROC = ROOT / os.getenv('PROCESSED_DIR', 'data/processed')

def list_and_download_captions(yt, vid):
    resp = yt.captions().list(part='snippet', videoId=vid).execute()
    rows = []
    for it in resp.get('items', []):
        cap_id = it['id']
        lang = it['snippet'].get('language')
        name = f"{vid}_{lang or 'und'}.srt"
        try:
            data = yt.captions().download(id=cap_id, tfmt='srt').execute()
            (RAW / 'captions').mkdir(parents=True, exist_ok=True)
            with open(RAW / 'captions' / name, 'wb') as f:
                f.write(data)
            rows.append({'videoId': vid, 'captionId': cap_id, 'lang': lang, 'file': str(RAW / 'captions' / name)})
        except Exception:
            rows.append({'videoId': vid, 'captionId': cap_id, 'lang': lang, 'file': None})
    return pd.DataFrame(rows)

if __name__ == "__main__":
    yt = yt_service()
    vids = pd.read_parquet(PROC / 'videos.parquet')['videoId'].tolist()
    frames = []
    for v in vids:
        try:
            frames.append(list_and_download_captions(yt, v))
        except Exception as e:
            print('caption error', v, e)
    if frames:
        out = pd.concat(frames, ignore_index=True)
        out.to_parquet(PROC / 'captions_index.parquet', index=False)
        print('Saved captions index →', PROC / 'captions_index.parquet')
