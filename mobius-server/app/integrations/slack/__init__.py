from app.core.config import settings
from app.integrations.base import IntegrationBase


class SlackIntegration(IntegrationBase):
    name = "slack"
    display_name = "Slack"
    auth_type = "oauth2"
    scopes = ["chat:write", "channels:read", "channels:history", "search:read", "users.profile:write"]
    base_api_url = "https://slack.com/api"
    auth_url = "https://slack.com/oauth/v2/authorize"
    token_url = "https://slack.com/api/oauth.v2.access"

    def _get_client_id(self) -> str:
        return settings.SLACK_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.SLACK_CLIENT_SECRET
