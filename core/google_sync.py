import gspread
from oauth2client.service_account import ServiceAccountCredentials
from core.resource_helper import resource_path

def append_to_google_sheet(sheet_name, row_values):
    print("⏳ Sending to Google Sheet:", row_values)

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_path = resource_path("creds.json")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)

        client = gspread.authorize(creds)

        sheet = client.open(sheet_name).worksheet("Sheet1")  # or whatever the tab is called

        sheet.append_row(row_values)
        print("✅ Data synced to Google Sheet.")
    except Exception as e:
        print("❌ Failed to sync with Google Sheet:", e)
