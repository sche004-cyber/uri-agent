import os
import io
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

class DriveService:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.token_path = self.project_root / "token.json"
        self.evidence_dir = self.project_root / "uri_workspace" / "evidence"
        self.service = None

    def connect(self) -> dict:
        if not self.token_path.exists():
            return {"success": False, "reason": "token.json not found."}
        try:
            creds = Credentials.from_authorized_user_file(self.token_path)
            self.service = build("drive", "v3", credentials=creds)
            return {"success": True, "mode": "READ_ONLY"}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    def search_drive(self, query, limit=3) -> dict:
        if not self.service:
            conn = self.connect()
            if not conn.get("success"): return conn
        try:
            drive_query = f"name contains '{query}' or fullText contains '{query}'"
            results = self.service.files().list(
                q=drive_query,
                pageSize=limit,
                fields="files(id, name, mimeType)",
                orderBy="modifiedTime desc"
            ).execute()
            return {"success": True, "files": results.get("files", [])}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    def download_file(self, file_id, file_name, mime_type) -> dict:
        if not self.service:
            conn = self.connect()
            if not conn.get("success"): return conn
            
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        safe_name = file_name.replace(":", "_")
        target_path = self.evidence_dir / safe_name

        try:
            if mime_type == 'application/vnd.google-apps.spreadsheet':
                request = self.service.files().export_media(
                    fileId=file_id, 
                    mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                target_path = target_path.with_suffix('.xlsx')
            elif mime_type == 'application/vnd.google-apps.document':
                request = self.service.files().export_media(
                    fileId=file_id, 
                    mimeType='application/pdf'
                )
                target_path = target_path.with_suffix('.pdf')
            else:
                request = self.service.files().get_media(fileId=file_id)
                
            fh = io.FileIO(target_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                
            return {"success": True, "path": str(target_path), "exported_name": target_path.name}
            
        except Exception as e:
            return {"success": False, "reason": str(e)}

    def purge_downloads(self) -> dict:
        """Securely delete all files currently stored in the evidence workspace."""
        if not self.evidence_dir.exists():
            return {"success": True, "deleted": 0}
            
        deleted_count = 0
        for file_path in self.evidence_dir.glob("*"):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception:
                    pass
                    
        return {"success": True, "deleted": deleted_count}
