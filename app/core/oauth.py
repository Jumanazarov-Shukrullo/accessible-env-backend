from authlib.integrations.starlette_client import OAuth

from app.core.config import settings


oauth = OAuth()

oauth.register(
    name="google",
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    api_base_url="https://openidconnect.googleapis.com/v1/",  # ← here
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",  # ← here
    client_id=settings.auth.google_client_id,
    client_secret=settings.auth.google_client_secret,
    client_kwargs={
        "scope": "openid email profile https://www.googleapis.com/auth/drive.metadata.readonly"
    },
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
)
