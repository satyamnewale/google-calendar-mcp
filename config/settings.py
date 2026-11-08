import os
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parents[1]

# Google Calendar configuration
TIMEZONE = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Asia/Kolkata")
LOCAL_TIMEZONE = ZoneInfo(TIMEZONE)

# Target calendar for this local server instance.
# "primary" means the authenticated user's primary calendar.
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

# OAuth files
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"

# Calendar defaults
DEFAULT_EVENT_DURATION_MINUTES = 60
DEFAULT_REMINDER_MINUTES = 10

# Event retrieval limits
MAX_RESULTS_LIMIT = 2500
DEFAULT_MAX_RESULTS = MAX_RESULTS_LIMIT

# Recurrence limits
MAX_RECURRENCE_OCCURRENCES = 500

# For indefinite recurring events, check conflicts
# over the next 90 days only.
INDEFINITE_RECURRENCE_CHECK_DAYS = 90

# Search configuration
SIMILARITY_THRESHOLD = 0.55

# Week configuration
WEEK_START_DAY = 0  # Monday