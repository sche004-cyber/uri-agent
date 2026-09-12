import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from uri_core.core.connection_status import _repo_root

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailSearchService:
    """
    Handles secure authentication and targeted email searching
    to fetch administrative context directly from Gmail.

    2026-09-12 (User directive): previously kept its OWN, independent
    pickle-based token.pickle, entirely separate from the JSON-based
    token.json every other Google-connected class (GmailService,
    DriveService, connection_status.py) reads and writes - so a
    connection the User actually completed via Settings > Connections
    was invisible here, and using this service would have started a
    SECOND, redundant OAuth consent flow. Now reads the exact same
    token.json (read-only here - this class never writes it; the one
    real consent flow lives in GmailService.connect(), started only
    from POST /connections/{id}/authorize) via the same _repo_root()
    every other Google-connected class already uses, so a connection
    made once is usable everywhere.
    """
    def __init__(self, credentials_path=None, token_path=None):
        credentials_root = _repo_root()
        self.credentials_path = credentials_path or os.path.join(credentials_root, "credentials.json")
        self.token_path = token_path or os.path.join(credentials_root, "token.json")
        self.service = None

    def authenticate(self) -> bool:
        """Authenticates using the token.json this install's one real
        Google consent flow (GmailService.connect()) already produced.
        Never launches an interactive consent flow itself - if no
        usable token exists yet, this honestly reports False rather
        than starting a second, redundant browser flow."""
        if not os.path.exists(self.token_path):
            return False

        try:
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        except Exception:
            return False

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    return False
            else:
                return False

        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception:
            return False

    def get_unread_count(self) -> dict:
        """The real, current unread count for the primary inbox label -
        one direct Gmail API call (labels.get), never estimated by
        counting a capped search result page. Returns {"success": bool,
        "unread_count": int} or {"success": False, "error": "..."}."""
        if not self.service:
            if not self.authenticate():
                return {
                    "success": False,
                    "error": "Gmail authentication failed or credentials.json/token.json missing.",
                }

        try:
            label = self.service.users().labels().get(userId='me', id='UNREAD').execute()
            return {"success": True, "unread_count": label.get('messagesUnread', 0)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_emails(self, query: str, max_results: int = 5) -> list:
        """Searches Gmail messages matching the administrative query."""
        if not self.service:
            if not self.authenticate():
                return [{"error": "Gmail authentication failed or credentials.json missing."}]
                
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            extracted_data = []
            for msg in messages:
                # Use format='full' (or omit format) to avoid API parameter errors
                msg_data = self.service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                snippet = msg_data.get('snippet', '')
                
                headers = msg_data.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                extracted_data.append({
                    "subject": subject,
                    "date": date,
                    "snippet": snippet
                })
            return extracted_data
        except Exception as e:
            return [{"error": str(e)}]
