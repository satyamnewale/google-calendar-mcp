
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parents[1]

# Google Calendar configuration
CALENDAR_ID = "primary"
TIMEZONE = "Asia/Kolkata"
LOCAL_TIMEZONE = ZoneInfo(TIMEZONE)

# OAuth files
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"

# Calendar defaults
DEFAULT_EVENT_DURATION_MINUTES = 60
DEFAULT_REMINDER_MINUTES = 10
DEFAULT_MAX_RESULTS = 250
MAX_RESULTS_LIMIT = 2500

# Search configuration
SIMILARITY_THRESHOLD = 0.55

# Week configuration
WEEK_START_DAY = 0  # Monday
