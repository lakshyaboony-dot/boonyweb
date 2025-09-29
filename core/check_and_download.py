import os
import datetime
from drive_auth import get_drive
import pytz

def check_and_download_latest(file_id, local_path):
    drive = get_drive()
    file = drive.CreateFile({'id': file_id})
    file.FetchMetadata(fields='modifiedDate, title')

    drive_time_str = file['modifiedDate']
    drive_time = datetime.datetime.strptime(drive_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc)

    if os.path.exists(local_path):
        local_time = datetime.datetime.fromtimestamp(os.path.getmtime(local_path), pytz.utc)
        print("📁 Local file modified:", local_time)
        print("☁️ Drive file modified:", drive_time)

        if drive_time <= local_time:
            print("✅ Local file is up-to-date.")
            return "up-to-date"
        else:
            print("⬇️ Drive version is newer. Downloading...")
    else:
        print("📂 Local file missing. Downloading from Drive...")

    file.GetContentFile(local_path)
    print("✅ Downloaded latest file to:", local_path)
    return "downloaded"

# Run when file is executed directly
if __name__ == "__main__":
    file_id = "1JvpHpg2DJH1uAx6h-iskCDWTa46xqsrI"
    local_path = "data/syllabus/user_list.xlsx"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    check_and_download_latest(file_id, local_path)
