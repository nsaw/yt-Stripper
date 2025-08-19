
import os
import pathlib
import pandas as pd
from dotenv import load_dotenv
from auth import yt_service

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
RAW = ROOT / os.getenv('RAW_DIR', 'data/raw')
PROC = ROOT / os.getenv('PROCESSED_DIR', 'data/processed')
CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')

def get_uploads_playlist_id(yt):
    resp = yt.channels().list(part='contentDetails', id=CHANNEL_ID).execute()
    items = resp.get('items', [])
    if not items:
        raise RuntimeError('Channel not found or no access.')
    return items[0]['contentDetails']['relatedPlaylists']['uploads']

def fetch_all_videos(yt, uploads_playlist_id):
    vids = []
    pageToken=None
    while True:
        resp = yt.playlistItems().list(
            part='contentDetails,snippet', playlistId=uploads_playlist_id, maxResults=50, pageToken=pageToken
        ).execute()
        for it in resp.get('items', []):
            vids.append({
                'videoId': it['contentDetails']['videoId'],
                'publishedAt': it['contentDetails']['videoPublishedAt'],
                'title': it['snippet'].get('title',''),
                'description': it['snippet'].get('description','')
            })
        pageToken = resp.get('nextPageToken')
        if not pageToken:
            break
    return pd.DataFrame(vids)

def fetch_thumbnails(yt, video_ids):
    # Download default thumbnail for quick features
    (ROOT / 'data/raw/thumbnails').mkdir(parents=True, exist_ok=True)
    resp = yt.videos().list(part='snippet', id=','.join(video_ids[:50])).execute()  # batch 50 at a time in caller
    rows = []
    for it in resp.get('items', []):
        sn = it['snippet']
        thumbs = sn.get('thumbnails', {})
        pick = thumbs.get('maxres') or thumbs.get('standard') or thumbs.get('high') or thumbs.get('medium') or thumbs.get('default')
        url = pick['url'] if pick else None
        rows.append({'videoId': it['id'], 'thumbnail': url})
    return pd.DataFrame(rows)

if __name__ == "__main__":
    yt = yt_service()
    uploads = get_uploads_playlist_id(yt)
    df = fetch_all_videos(yt, uploads)
    df.to_parquet(PROC / 'videos.parquet', index=False)
    # thumbnails urls (download later in analysis step if needed)
    thumb_rows = []
    for i in range(0, len(df), 50):
        thumb_rows.append(fetch_thumbnails(yt, df['videoId'].iloc[i:i+50].tolist()))
    if thumb_rows:
        thumbs = pd.concat(thumb_rows, ignore_index=True)
        thumbs.to_parquet(PROC / 'thumbnails.parquet', index=False)
    print(f"Saved {len(df)} videos -> {PROC/'videos.parquet'} and thumbnails map.")
