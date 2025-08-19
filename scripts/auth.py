
import pathlib
import json
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/yt-analytics.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl'  # captions download
]

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLIENT_SECRET = ROOT / 'client_secret.json'

def get_creds(token_name='token_default.json'):
    # Try service account first
    if CLIENT_SECRET.exists():
        try:
            with open(CLIENT_SECRET, 'r') as f:
                cred_data = json.load(f)
                if cred_data.get('type') == 'service_account':
                    return service_account.Credentials.from_service_account_file(
                        str(CLIENT_SECRET), scopes=SCOPES
                    )
        except Exception:
            pass
    
    # Fallback to OAuth2 flow
    token_path = ROOT / token_name
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
    return creds

def yt_service(creds=None):
    creds = creds or get_creds()
    return build('youtube', 'v3', credentials=creds, static_discovery=False)

def yta_service(creds=None):
    creds = creds or get_creds()
    return build('youtubeAnalytics', 'v2', credentials=creds, static_discovery=False)
