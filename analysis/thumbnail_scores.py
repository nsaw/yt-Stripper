
import os
import pathlib
import urllib.request
import cv2
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from PIL import Image
import pytesseract

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
PROC = ROOT / os.getenv('PROCESSED_DIR', 'data/processed')
RAW = ROOT / os.getenv('RAW_DIR', 'data/raw')
REPORTS = ROOT / os.getenv('REPORTS_DIR', 'reports')
(REPORTS).mkdir(parents=True, exist_ok=True)

def download(url, path):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = r.read()
        with open(path, 'wb') as f:
            f.write(data)
        return True
    except Exception:
        return False

def features(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(g, (3,3), 0)
    lap = cv2.Laplacian(blur, cv2.CV_64F).var()  # sharpness
    # brightness/contrast
    mean = float(np.mean(g))
    contrast = float(np.std(g))
    # text density (OCR length / area)
    try:
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        txt = pytesseract.image_to_string(pil)
        text_density = len(txt.strip()) / (img.shape[0]*img.shape[1])
    except Exception:
        text_density = np.nan
    return {'sharpness': lap, 'brightness': mean, 'contrast': contrast, 'text_density': text_density}

if __name__ == '__main__':
    thumbs = pd.read_parquet(PROC / 'thumbnails.parquet')
    out_rows = []
    (RAW/'thumb_dl').mkdir(parents=True, exist_ok=True)
    for _, r in thumbs.iterrows():
        url = r['thumbnail']
        vid = r['videoId']
        if not url:
            continue
        path = RAW/'thumb_dl'/f'{vid}.jpg'
        if not path.exists():
            ok = download(url, path)
            if not ok:
                continue
        img = cv2.imread(str(path))
        if img is None:
            continue
        out = features(img)
        out['videoId'] = vid
        out_rows.append(out)
    df = pd.DataFrame(out_rows)
    df.to_parquet(PROC / 'thumbnail_features.parquet', index=False)
    print('Saved →', PROC / 'thumbnail_features.parquet')
