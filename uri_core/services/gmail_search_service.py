import os
from googleapiclient.discovery import build

from uri_core.core.connection_status import _repo_root
from uri_core.core.google_auth_common import load_usable_credentials, resolve_google_token_path

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailSearchService:
    """
    Handles secure authentication and targeted email searching
    to fetch administrative context directly from Gmail.

    Per-user mailbox isolation (M32 A1-3): when user_id is provided,
    token_path resolves strictly to that user's own scoped token.json.
    credentials.json remains install-wide.
    """
    def __init__(self, credentials_path=None, token_path=None, user_id=None):
        credentials_root = _repo_root()
        self.credentials_path = credentials_path or os.path.join(credentials_root, "credentials.json")
        self.user_id = user_id
        self.token_path = token_path or resolve_google_token_path(user_id)
        self.service = None

    def authenticate(self) -> bool:
        """Authenticates using the token.json for this user or install.
        Never launches an interactive consent flow itself - if no
        usable token exists yet, this honestly reports False rather
        than starting a second, redundant browser flow."""
        creds = load_usable_credentials(
            token_path=self.token_path,
            scopes=SCOPES,
            allow_refresh=True,
        )
        if creds is None:
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
