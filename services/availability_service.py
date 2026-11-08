from datetime import datetime, timedelta

from auth.google_auth import get_calendar_service
from config.settings import CALENDAR_ID, TIMEZONE

from utils.datetime_utils import to_rfc3339
from utils.validators import (
    validate_event_time,
    validate_time_range,
)

def check_availability(
    start_date: datetime,
    end_date: datetime,
    calendar_id: str = CALENDAR_ID,
):
    validate_time_range(start_date, end_date)

    service = get_calendar_service()

    body = {
        "timeMin": to_rfc3339(start_date),
        "timeMax": to_rfc3339(end_date),
        "timeZone": TIMEZONE,
        "items": [
            {"id": calendar_id}
        ],
    }

    response = service.freebusy().query(
        body=body
    ).execute()

    calendar_data = response.get(
        "calendars", {}
    ).get(calendar_id, {})

    errors = calendar_data.get("errors", [])

    if errors:
        raise RuntimeError(
            f"Google FreeBusy API returned errors: {errors}"
        )

    busy_periods = calendar_data.get("busy", [])

    return {
        "available": len(busy_periods) == 0,
        "busy_periods": busy_periods,
    }

def find_conflicts(
    start_date: datetime,
    end_date: datetime,
):
    result = check_availability(start_date, end_date)

    return result["busy_periods"]

def get_available_slots(
    start_date: datetime,
    end_date: datetime,
    duration_minutes: int = 60,
):
    """Return uninterrupted free periods meeting the duration requirement."""
    validate_event_time(start_date, end_date)

    if not isinstance(duration_minutes, int) or isinstance(duration_minutes, bool):
        raise ValueError("Duration must be an integer.")

    if not 1 <= duration_minutes <= 1440:
        raise ValueError("Duration must be between 1 and 1440 minutes.")

    busy_periods = find_conflicts(start_date, end_date)

    busy = sorted(
        (
            datetime.fromisoformat(
                item["start"].replace("Z", "+00:00")
            ),
            datetime.fromisoformat(
                item["end"].replace("Z", "+00:00")
            ),
        )
        for item in busy_periods
    )

    slots = []
    cursor = start_date

    for busy_start, busy_end in busy:
        if busy_start > cursor:
            if busy_start - cursor >= timedelta(
                minutes=duration_minutes
            ):
                slots.append({
                    "start": cursor.isoformat(),
                    "end": busy_start.isoformat(),
                })

        cursor = max(cursor, busy_end)

    if end_date - cursor >= timedelta(minutes=duration_minutes):
        slots.append({
            "start": cursor.isoformat(),
            "end": end_date.isoformat(),
        })

    return slots

def find_occurrence_conflicts(
    occurrences: list[tuple[datetime, datetime]],
    busy_periods: list[dict],
) -> list[dict]:
    """
    Compare every event occurrence against calendar busy periods.

    Two intervals overlap when:

        occurrence_start < busy_end
        AND
        occurrence_end > busy_start
    """

    conflicts = []

    for occurrence_start, occurrence_end in occurrences:

        for busy_period in busy_periods:

            busy_start = datetime.fromisoformat(
                busy_period["start"].replace("Z", "+00:00")
            )

            busy_end = datetime.fromisoformat(
                busy_period["end"].replace("Z", "+00:00")
            )

            if (
                occurrence_start < busy_end
                and occurrence_end > busy_start
            ):

                conflicts.append({
                    "occurrence": {
                        "start": occurrence_start.isoformat(),
                        "end": occurrence_end.isoformat(),
                    },
                    "existing_event": {
                        "start": busy_start.isoformat(),
                        "end": busy_end.isoformat(),
                    },
                })

    return conflicts