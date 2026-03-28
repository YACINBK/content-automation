import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv(override=True)

# The specific API scope needed to upload files to Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
TOKEN_FILE = 'drive_token.json'

def authenticate_drive():
    """Handles OAuth2 authentication for Google Drive and stores the token locally."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(drive_service, folder_name="Niche"):
    """
    Searches for a folder by name. If not found, creates it.
    Uses 'drive.file' scope, so it will only see folders it created itself.
    """
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    
    if files:
        return files[0].get('id')
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        print(f"📁 Created new Google Drive Folder: {folder_name}")
        return folder.get('id')

def upload_to_drive(drive_service, file_path, folder_id=None):
    """
    Uploads a file to Google Drive.
    Returns the Google Drive File ID.
    If folder_id is provided, the file is placed precisely in that folder.
    """
    filename = os.path.basename(file_path)
    print(f"☁️  Uploading to Google Drive: {filename}...")
    
    file_metadata = {'name': filename}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    # Resumable upload for large files
    media = MediaFileUpload(file_path, resumable=True)
    
    request = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   {int(status.progress() * 100)}% uploaded to Google Drive...")

    file_id = response.get('id')
    print(f"✅ G-Drive Upload Complete! File ID: {file_id}")
    return file_id

if __name__ == "__main__":
    # Standalone test connection
    service = authenticate_drive()
    print("Google Drive API Authenticated OK. Service object ready.")
