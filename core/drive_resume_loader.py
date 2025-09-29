# core/drive_resume_loader.py

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import os

def authenticate_drive():
    """Authenticate using a service account JSON and return a GoogleDrive object."""
    scope = ['https://www.googleapis.com/auth/drive']
    creds_path = "core/creds.json"

    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Service account JSON not found at: {creds_path}")

    try:
        gauth = GoogleAuth()
        gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        drive = GoogleDrive(gauth)
        print("✅ Google Drive authenticated successfully.")
        return drive
    except Exception as e:
        print(f"⚠️ Google Drive authentication failed: {e}")
        raise

def list_resume_types(drive, parent_folder_name="resume"):
    """
    Returns a dictionary of resume type folders inside the main 'resume' folder.
    Example output:
    {
        'Chronological': '1aB...xyz',
        'Functional': '1cD...abc',
        ...
    }
    """
    folders = {}
    parent_query = (
        f"title='{parent_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    parent_folders = drive.ListFile({'q': parent_query}).GetList()

    if not parent_folders:
        raise Exception(f"No folder named '{parent_folder_name}' found in Google Drive.")

    parent_id = parent_folders[0]['id']
    subfolder_query = (
        f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    subfolders = drive.ListFile({'q': subfolder_query}).GetList()

    for folder in subfolders:
        folders[folder['title']] = folder['id']

    return folders

def list_docx_examples(drive, folder_id):
    """
    Returns a list of .docx files inside the given folder.
    Each item includes: title, file ID, and webViewLink.
    """
    query = (
        f"'{folder_id}' in parents and mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' and trashed=false"
    )
    files = drive.ListFile({'q': query}).GetList()

    results = []
    for f in files:
        results.append({
            "title": f['title'],
            "id": f['id'],
            "webViewLink": f['alternateLink']
        })

    return results
def get_excel_file_by_name(drive, filename="resume_fields"):
    query = f"title='{filename}' and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and trashed=false"
    result = drive.ListFile({'q': query}).GetList()

    if not result:
        raise FileNotFoundError(f"'{filename}' not found in your Google Drive.")
    
    return result[0]  # Return first match
def get_file_id_and_title(drive, filename, mime_type):
    query = f"title='{filename}' and mimeType='{mime_type}' and trashed=false"
    result = drive.ListFile({'q': query}).GetList()
    if not result:
        raise FileNotFoundError(f"'{filename}' not found on Google Drive.")
    file = result[0]
    return file["id"], file["title"]  # ✅ Now it's a tuple!

    