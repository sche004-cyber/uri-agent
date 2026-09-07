import os


class DriveSpreadsheetFetcher:
    """Reads rows from a real Google Sheet via a service account. Never
    invents data: when no service-account credentials are configured,
    or the API call fails, this reports the real reason honestly
    (status "unavailable"/"error") - it must never return fabricated
    rows presented as if they were real records (M19 audit finding:
    this tool previously returned invented student names/CGPAs as a
    silent "local_fallback_cache" whenever credentials were absent,
    which the Brain and the user had no way to distinguish from real
    data)."""

    def __init__(self, credentials_path="uri_workspace/credentials.json"):
        self.credentials_path = os.path.normpath(credentials_path)

    def fetch_rows(self, **kwargs):
        spreadsheet_id = kwargs.get("spreadsheet_id")
        range_name = kwargs.get("range_name", "Sheet1!A1:D10")

        if not spreadsheet_id:
            return {
                "status": "input_required",
                "message": "No spreadsheet_id was given, so URI could not fetch any rows.",
            }

        if not os.path.exists(self.credentials_path):
            return {
                "status": "unavailable",
                "message": "URI could not read this spreadsheet.",
                "error": (
                    "No Google service-account credentials are configured "
                    f"({self.credentials_path} does not exist)."
                ),
                "spreadsheet_id": spreadsheet_id,
            }

        try:
            import gspread

            gc = gspread.service_account(filename=self.credentials_path)
            sheet = gc.open_by_key(spreadsheet_id)
            worksheet = sheet.sheet1
            rows = worksheet.get_all_records()
        except Exception as error:
            return {
                "status": "unavailable",
                "message": "URI could not read this spreadsheet.",
                "error": str(error),
                "spreadsheet_id": spreadsheet_id,
            }

        return {
            "status": "success",
            "source": "live_google_sheets",
            "spreadsheet_id": spreadsheet_id,
            "range": range_name,
            "rows": rows,
        }
