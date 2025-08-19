
import os
import pathlib
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from auth import yt_service

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
PROC = ROOT / os.getenv('PROCESSED_DIR', 'data/processed')

def fetch_comments_for_video(yt, vid):
    allrows = []
    pageToken=None
    while True:
        resp = yt.commentThreads().list(
            part='snippet,replies',
            videoId=vid,
            maxResults=100,
            pageToken=pageToken,
            textFormat='plainText'
        ).execute()
        for it in resp.get('items', []):
            top = it['snippet']['topLevelComment']['snippet']
            allrows.append({
                'videoId': vid,
                'type': 'top',
                'text': top.get('textDisplay',''),
                'likeCount': top.get('likeCount',0),
                'publishedAt': top.get('publishedAt')
            })
            for r in it.get('replies', {}).get('comments', []):
                rs = r['snippet']
                allrows.append({
                    'videoId': vid,
                    'type': 'reply',
                    'text': rs.get('textDisplay',''),
                    'likeCount': rs.get('likeCount',0),
                    'publishedAt': rs.get('publishedAt')
                })
        pageToken = resp.get('nextPageToken')
        if not pageToken:
            break
    return pd.DataFrame(allrows)

if __name__ == "__main__":
    yt = yt_service()
    vids = pd.read_parquet(PROC / 'videos.parquet')['videoId'].tolist()
    frames = []
    for v in tqdm(vids, desc='comments'):
        try:
            frames.append(fetch_comments_for_video(yt, v))
        except Exception as e:
            print('error', v, e)
    if frames:
        out = pd.concat(frames, ignore_index=True)
        out.to_parquet(PROC / 'comments.parquet', index=False)
        print('Saved comments →', PROC / 'comments.parquet')
