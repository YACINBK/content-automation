"""
Google Drive Uploader
=====================
Handles authentication and file upload to Google Drive.

Usage (standalone test):
    python drive_uploader.py --file path/to/file.mp4 --folder "Poetry Videos"

Usage (from code):
    from drive_uploader import DriveUploader
    uploader = DriveUploader()
    folder_id = uploader.get_or_create_folder("Poetry Videos")
    url = uploader.upload_file("final_videos/myvideo.mp4", folder_id, "video/mp4")
"""

import os
import logging
import argparse
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

# Only request permission to manage files this app creates
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Default paths (relative to the project root)
DEFAULT_CREDENTIALS_PATH = "credentials.json"
DEFAULT_TOKEN_PATH = "token.json"


class DriveUploader:
    """
    Manages Google Drive authentication and file uploads.

    On the very first run, a browser window opens for OAuth2 consent.
    A `token.json` is then cached so subsequent runs are fully headless.
    """

    def __init__(
        self,
        credentials_path: str = DEFAULT_CREDENTIALS_PATH,
        token_path: str = DEFAULT_TOKEN_PATH,
    ):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self._service = None

    # ------------------------------------------------------------------
    # Internal: lazy-initialise the Drive API service
    # ------------------------------------------------------------------
    def _get_service(self):
        if self._service:
            return self._service

        creds = None

        # Load cached token if it exists
        if Path(self.token_path).exists():
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # If there are no (valid) credentials, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("🔄 Refreshing expired Drive token...")
                creds.refresh(Request())
            else:
                if not Path(self.credentials_path).exists():
                    raise FileNotFoundError(
                        f"❌ Google credentials file not found: '{self.credentials_path}'\n"
                        f"   Download it from Google Cloud Console → APIs & Services → Credentials."
                    )
                logger.info("🌐 Opening browser for Google Drive authentication...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for next run
            with open(self.token_path, "w") as token_file:
                token_file.write(creds.to_json())
            logger.info(f"✅ Drive token saved to: {self.token_path}")

        self._service = build("drive", "v3", credentials=creds)
        return self._service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_or_create_folder(self, folder_id_or_name: str) -> str:
        """
        Return a Drive folder ID.
        1. First, tries to verify if folder_id_or_name is a valid ID.
        2. If not, searches for a folder with that name.
        3. If no folder is found by name, creates it.
        """
        service = self._get_service()

        # 1. Try treating it as an ID first
        if folder_id_or_name and len(folder_id_or_name) > 20:
            try:
                folder = service.files().get(
                    fileId=folder_id_or_name, 
                    fields="id, name, mimeType, trashed"
                ).execute()
                
                if (folder.get("mimeType") == "application/vnd.google-apps.folder" 
                    and not folder.get("trashed")):
                    logger.info(f"📁 Drive folder verified by ID: '{folder['name']}' ({folder['id']})")
                    return folder["id"]
            except Exception:
                # Not a valid ID or no access, fall through to search by name
                pass

        # 2. Search for an existing folder with this exact name
        query = (
            f"name='{folder_id_or_name}' "
            f"and mimeType='application/vnd.google-apps.folder' "
            f"and trashed=false"
        )
        results = (
            service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )
        files = results.get("files", [])

        if files:
            folder_id = files[0]["id"]
            logger.info(f"📁 Drive folder found by name: '{folder_id_or_name}' (id={folder_id})")
            return folder_id

        # 3. Create the folder (since it's not a valid ID and doesn't exist by name)
        folder_metadata = {
            "name": folder_id_or_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = service.files().create(body=folder_metadata, fields="id").execute()
        folder_id = folder.get("id")
        logger.info(f"📁 Drive folder created: '{folder_id_or_name}' (id={folder_id})")
        return folder_id

    def upload_file(
        self,
        local_path: str,
        drive_folder_id: str,
        mime_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload *local_path* to the given Drive folder.

        Returns the webViewLink URL of the uploaded file.
        """
        service = self._get_service()
        local_path = Path(local_path)

        if not local_path.exists():
            raise FileNotFoundError(f"❌ File to upload does not exist: {local_path}")

        file_metadata = {
            "name": local_path.name,
            "parents": [drive_folder_id],
        }

        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)

        logger.info(f"☁️  Uploading '{local_path.name}' to Drive...")
        uploaded = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink, name",
            )
            .execute()
        )

        url = uploaded.get("webViewLink", "")
        logger.info(f"✅ Upload complete: {local_path.name} → {url}")
        return url

    def delete_local(self, local_path: str) -> None:
        """Delete a local file, logging a warning if it cannot be removed."""
        try:
            Path(local_path).unlink(missing_ok=True)
            logger.info(f"🗑️  Deleted local file: {local_path}")
        except Exception as exc:
            logger.warning(f"⚠️  Could not delete local file '{local_path}': {exc}")


# ---------------------------------------------------------------------------
# Standalone test / CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(description="Upload a file to Google Drive")
    parser.add_argument("--file", required=True, help="Local file path to upload")
    parser.add_argument("--folder", default="Test Uploads", help="Drive folder name")
    parser.add_argument(
        "--credentials", default=DEFAULT_CREDENTIALS_PATH, help="Path to credentials.json"
    )
    args = parser.parse_args()

    uploader = DriveUploader(credentials_path=args.credentials)
    folder_id = uploader.get_or_create_folder(args.folder)
    url = uploader.upload_file(args.file, folder_id)
    print(f"\n🔗 File available at: {url}")
