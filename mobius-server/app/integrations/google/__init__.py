from app.core.config import settings
from app.integrations.base import IntegrationBase
from urllib.parse import urlencode


class GoogleIntegration(IntegrationBase):
    name = "google"
    display_name = "Google"
    auth_type = "oauth2"
    scopes = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/tasks",
    ]
    base_api_url = "https://www.googleapis.com"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"

    def _get_client_id(self) -> str:
        return settings.GOOGLE_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.GOOGLE_CLIENT_SECRET

    def get_authorize_url(self, user_id: str, base_url: str) -> str:
        params = {
            "client_id": self._get_client_id(),
            "redirect_uri": f"{base_url}/connect/{self.name}/callback",
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": user_id,
        }
        return f"{self.auth_url}?{urlencode(params)}"
