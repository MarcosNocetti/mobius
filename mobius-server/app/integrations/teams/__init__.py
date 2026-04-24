from app.core.config import settings
from app.integrations.base import IntegrationBase


class TeamsIntegration(IntegrationBase):
    name = "teams"
    display_name = "Microsoft Teams"
    auth_type = "oauth2"
    scopes = [
        "https://graph.microsoft.com/Chat.ReadWrite",
        "https://graph.microsoft.com/Team.ReadBasic.All",
        "https://graph.microsoft.com/OnlineMeetings.ReadWrite",
    ]
    base_api_url = "https://graph.microsoft.com/v1.0"

    @property
    def auth_url(self) -> str:
        return f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/authorize"

    @property
    def token_url(self) -> str:
        return f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/token"

    def _get_client_id(self) -> str:
        return settings.AZURE_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.AZURE_CLIENT_SECRET
