import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailSearchService:
    """
    Handles secure authentication and targeted email searching 
    to fetch administrative context directly from Gmail.
    """
    def __init__(self, credentials_path=None, token_path=None):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.credentials_path = credentials_path or os.path.join(project_root, "credentials.json")
        self.token_path = token_path or os.path.join(project_root, "token.pickle")
        self.service = None

    def authenticate(self) -> bool:
        """Authenticates securely using OAuth2 tokens, prompting user if necessary."""
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
                
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception:
            return False

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
