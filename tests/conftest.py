
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_calendar_service():
    """Mock the synchronous Google Calendar API client."""

    service = MagicMock()

    events = service.events.return_value

    events.get.return_value.execute.return_value = {
        "id": "test_event_001",
        "etag": '"test-etag-001"',
        "summary": "Team Meeting",
        "description": "Weekly team discussion",
        "location": "Office",
        "start": {
            "dateTime": "2026-11-10T10:00:00+05:30",
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": "2026-11-10T11:00:00+05:30",
            "timeZone": "Asia/Kolkata",
        },
        "status": "confirmed",
    }

    events.list.return_value.execute.return_value = {
        "items": [],
        "nextPageToken": None,
    }

    events.insert.return_value.execute.return_value = {
        "id": "new_event_001",
        "summary": "New Meeting",
        "status": "confirmed",
    }

    events.update.return_value.execute.return_value = {
        "id": "test_event_001",
        "etag": '"test-etag-001"',
        "summary": "Updated Meeting",
        "status": "confirmed",
    }

    events.delete.return_value.execute.return_value = {}

    service.calendarList.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "primary",
                "summary": "Primary Calendar",
                "primary": True,
                "timeZone": "Asia/Kolkata",
            }
        ]
    }

    service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {
            "primary": {
                "busy": [],
            }
        }
    }

    return service


@pytest.fixture
def sample_timed_event():
    return {
        "id": "test_event_001",
        "etag": '"test-etag-001"',
        "summary": "Team Meeting",
        "description": "Weekly team discussion",
        "location": "Office",
        "start": {
            "dateTime": "2026-11-10T10:00:00+05:30",
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": "2026-11-10T11:00:00+05:30",
            "timeZone": "Asia/Kolkata",
        },
        "status": "confirmed",
    }


@pytest.fixture
def sample_all_day_event():
    return {
        "id": "test_event_002",
        "summary": "Project Submission",
        "description": "Submit the project",
        "start": {"date": "2026-11-10"},
        "end": {"date": "2026-11-11"},
        "status": "confirmed",
    }


@pytest.fixture
def sample_busy_periods():
    return [
        {
            "start": "2026-11-10T10:00:00+05:30",
            "end": "2026-11-10T11:00:00+05:30",
        },
        {
            "start": "2026-11-10T14:00:00+05:30",
            "end": "2026-11-10T15:00:00+05:30",
        },
    ]


@pytest.fixture
def sample_event_updates():
    return {
        "summary": "Updated Team Meeting",
        "description": "Updated meeting agenda",
        "location": "Conference Room",
    }
