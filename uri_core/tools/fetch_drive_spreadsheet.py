import os
import json

class DriveSpreadsheetFetcher:
    def __init__(self, credentials_path="uri_workspace/credentials.json"):
        self.credentials_path = os.path.normpath(credentials_path)

    def fetch_rows(self, **kwargs):
        spreadsheet_id = kwargs.get("spreadsheet_id", "mock_id")
        range_name = kwargs.get("range_name", "Sheet1!A1:D10")
        
        # If real Google API credentials exist, use gspread / googleapiclient
        if os.path.exists(self.credentials_path):
            try:
                import gspread
                gc = gspread.service_account(filename=self.credentials_path)
                sheet = gc.open_by_key(spreadsheet_id)
                worksheet = sheet.sheet1
                data = worksheet.get_all_records()
                return {"source": "live_google_sheets", "rows": data}
            except Exception as e:
                return {"status": "error", "message": f"Google Sheets API error: {str(e)}"}
        
        # Fallback administrative simulation for NIT Sikkim records
        return {
            "source": "local_fallback_cache",
            "spreadsheet_id": spreadsheet_id,
            "range": range_name,
            "rows": [
                {"Roll": "BTECH-2026-001", "Name": "Aarav Sharma", "Department": "CSE", "CGPA": 8.7},
                {"Roll": "BTECH-2026-002", "Name": "Priya Rai", "Department": "ECE", "CGPA": 9.1},
                {"Roll": "BTECH-2026-003", "Name": "Tenzing Bhutia", "Department": "EEE", "CGPA": 8.4}
            ],
            "note": "Place your Google service account JSON at uri_workspace/credentials.json for live cloud sync."
        }
