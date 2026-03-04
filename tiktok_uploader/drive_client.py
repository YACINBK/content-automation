"""
drive_client.py
===============
Google Drive helper for the TikTok Scheduler pipeline.

Responsibilities:
  - Authenticate via OAuth2 (credentials.json → token.json)
  - List all .mp4 files inside a given folder ID
  - Download a Drive file to a local path

Scope: drive.readonly — we only need to READ files, not write/delete anything.
"""

import io
import json
import logging
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

# Read-only scope — safest option for a download-only client
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

DEFAULT_CREDENTIALS_PATH = "credentials.json"
DEFAULT_TOKEN_PATH       = "token.json"


class DriveClient:
    """
    Lightweight Google Drive read-only client.

    First run: opens a browser window for OAuth consent.
    Subsequent runs: fully headless via cached token.json.
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
    # Private: lazy-build the Drive API service
    # ------------------------------------------------------------------
    def _get_service(self):
        if self._service:
            return self._service

        creds = None

        if Path(self.token_path).exists():
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("🔄 Refreshing expired Drive token...")
                creds.refresh(Request())
            else:
                if not Path(self.credentials_path).exists():
                    raise FileNotFoundError(
                        f"❌ credentials.json not found at '{self.credentials_path}'.\n"
                        "   Download it from Google Cloud Console → APIs & Services → Credentials."
                    )
                logger.info("🌐 Opening browser for Google Drive authentication...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_path, "w") as f:
                f.write(creds.to_json())
            logger.info(f"✅ Drive token saved → {self.token_path}")

        self._service = build("drive", "v3", credentials=creds)
        return self._service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_mp4_files(self, folder_id: str) -> list[dict]:
        """
        Return all MP4 files directly inside *folder_id*.

        Each dict has: id, name, size (bytes as str).
        Results are sorted by name (ascending) for deterministic ordering.
        """
        service = self._get_service()
        query = (
            f"'{folder_id}' in parents "
            f"and mimeType='video/mp4' "
            f"and trashed=false"
        )
        results = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name, size)",
                orderBy="name",
                pageSize=1000,
            )
            .execute()
        )
        files = results.get("files", [])
        logger.info(f"📂 Found {len(files)} MP4 file(s) in Drive folder {folder_id}")
        return files

    def list_video_pairs(self, folder_id: str) -> list[dict]:
        """
        Return a list of paired video+metadata dicts for every .mp4 that has
        a matching *_metadata.json* in the same Drive folder.

        Naming convention expected by the content pipeline:
            custom_poem_20260302_021132.mp4
            custom_poem_20260302_021132_metadata.json

        Each returned dict has:
            video_id    – Drive file ID of the .mp4
            video_name  – filename of the .mp4
            meta_id     – Drive file ID of the _metadata.json (or None)
            meta_name   – filename of the JSON (or None)
        """
        service = self._get_service()

        # Fetch all files in one request (videos + JSONs)
        query = (
            f"'{folder_id}' in parents "
            f"and trashed=false "
            f"and (mimeType='video/mp4' or mimeType='application/json' "
            f"     or name contains '_metadata.json')"
        )
        results = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name, mimeType)",
                orderBy="name",
                pageSize=1000,
            )
            .execute()
        )
        all_files = results.get("files", [])

        # Index JSON files by their stem (e.g. "custom_poem_20260302_021132_metadata")
        json_index: dict[str, dict] = {}
        for f in all_files:
            if f["name"].endswith(".json"):
                json_index[f["name"]] = f

        # Build pairs for every .mp4
        pairs = []
        for f in all_files:
            if not f["name"].endswith(".mp4"):
                continue
            stem = f["name"][:-4]  # remove .mp4
            meta_name = f"{stem}_metadata.json"
            meta_file = json_index.get(meta_name)

            pairs.append({
                "video_id":   f["id"],
                "video_name": f["name"],
                "meta_id":    meta_file["id"]   if meta_file else None,
                "meta_name":  meta_file["name"] if meta_file else None,
            })

        logger.info(
            f"📂 Found {len(pairs)} video(s) in folder "
            f"({sum(1 for p in pairs if p['meta_id'])} with metadata)."
        )
        return pairs

    def download_json(self, file_id: str) -> dict:
        """
        Download a JSON file from Drive and return its parsed content as a dict.
        No local file is written — content is kept in memory.
        """
        service = self._get_service()
        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = json.loads(buf.getvalue().decode("utf-8"))
        logger.info(f"📄 Downloaded JSON metadata (id={file_id})")
        return data

    def download_file(self, file_id: str, dest_path: str) -> str:
        """
        Download *file_id* from Drive to *dest_path*.

        Returns the resolved local path.
        """
        service = self._get_service()
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        with open(dest, "wb") as f:
            f.write(buf.getvalue())

        logger.info(f"⬇️  Downloaded {file_id} → {dest}")
        return str(dest)
