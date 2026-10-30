from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Project root: calendar-mcp/
BASE_DIR = Path(__file__).resolve().parents[1]

CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.events.freebusy",
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
]


def get_calendar_credentials():
    """
    Load existing Google OAuth credentials.
    Refresh expired credentials or initiate OAuth login.
    Save the resulting credentials in token.json.
    """

    credentials = None

    # 1. Load previously authorized credentials
    if TOKEN_PATH.exists():
        try:
            credentials = Credentials.from_authorized_user_file(
                str(TOKEN_PATH),
                SCOPES
            )
        except (ValueError, OSError):
            credentials = None

    # 2. Refresh expired credentials
    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError:
            credentials = None

    # 3. Start OAuth flow if credentials are missing or invalid
    if not credentials or not credentials.valid:

        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"OAuth credentials not found: {CREDENTIALS_PATH}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            SCOPES
        )

        credentials = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="consent"
        )

    # 4. Save credentials for future use
    TOKEN_PATH.write_text(
        credentials.to_json(),
        encoding="utf-8"
    )

    return credentials


def get_calendar_service():
    """
    Build and return an authenticated Google Calendar API client.
    """

    credentials = get_calendar_credentials()

    service = build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False
    )

    return service