import os
import json
import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv(override=True)

# The specific API scope needed to upload videos
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")

def authenticate_youtube():
    """Handles the OAuth2 authentication and stores the token locally."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return build('youtube', 'v3', credentials=creds)

def build_metadata(project_name, config_path):
    """Pull the title and description from the project's JSON config."""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Build a human-readable title from the project name
    title = project_name.replace('_', ' ').title()
    title = f"POV: {title} #Shorts"
    
    # Use the last narrative line as the CTA description
    script = config.get("narrative_script", [])
    cta_line = script[-1] if script else "Link in bio."
    
    description = (
        f"{cta_line}\n\n"
        "To upgrade your biological firmware, the 7-Day Dopamine Protocol is in the bio.\n\n"
        "#Shorts #psychology #dopamine #mindset #darkproductivity"
    )
    
    tags = ['psychology', 'dopamine', 'mindset', 'productivity', 'dark productivity',
            'self improvement', 'shorts', project_name.replace('_', ' ')]
    
    return title, description, tags

def upload_short(youtube, file_path, title, description, tags, privacy='private', category_id="27"):
    """Uploads the video to YouTube as a Short."""
    print(f"📤 Uploading: {title}")
    
    body = {
        'snippet': {
            'title': title[:100],  # YouTube title limit
            'description': description,
            'tags': tags,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': privacy,  # 'private' by default — review before publishing
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype='video/mp4')
    
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   {int(status.progress() * 100)}% uploaded...")

    video_id = response['id']
    print(f"✅ Upload Complete! YouTube ID: {video_id}")
    return video_id


if __name__ == "__main__":
    # Standalone test — will prompt OAuth login if no token.json exists
    yt_service = authenticate_youtube()
    print("Authentication OK. Service object ready.")