from app.core.config import settings
from app.integrations.base import IntegrationBase


class AzureDevOpsIntegration(IntegrationBase):
    name = "azure_devops"
    display_name = "Azure DevOps"
    auth_type = "oauth2"
    scopes = ["499b84ac-1321-427f-aa17-267ca6975798/.default"]
    base_api_url = "https://dev.azure.com"

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
