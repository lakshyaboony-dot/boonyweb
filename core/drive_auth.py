from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

class CompatibleCredentials:
    def __init__(self, creds):
        self.creds = creds
        self.creds.refresh(Request())  # refresh right away

    @property
    def access_token(self):
        return self.creds.token

    @property
    def access_token_expired(self):
        return False  # We just refreshed it

    def authorize(self, http):
        return http  # PyDrive2 doesn't actually use this in service mode

def get_drive():
    raw_creds = Credentials.from_service_account_file(
        "creds.json", scopes=["https://www.googleapis.com/auth/drive"]
    )
    gauth = GoogleAuth()
    gauth.auth_method = "service"
    gauth.credentials = CompatibleCredentials(raw_creds)
    return GoogleDrive(gauth)
