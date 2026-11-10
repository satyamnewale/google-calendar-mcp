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
    slot_interval_minutes: int = 15,
    max_suggestions: int = 10,
):
    """
    Generate fixed-duration meeting slots inside confirmed free windows.

    duration_minutes:
        Duration of each suggested meeting.

    slot_interval_minutes:
        Difference between consecutive candidate start times.

    max_suggestions:
        Maximum number of candidate slots returned.
    """

    validate_time_range(start_date, end_date)

    if (
        isinstance(duration_minutes, bool)
        or not isinstance(duration_minutes, int)
        or not 1 <= duration_minutes <= 1440
    ):
        raise ValueError(
            "Duration must be an integer between 1 and 1440 minutes."
        )

    if (
        isinstance(slot_interval_minutes, bool)
        or not isinstance(slot_interval_minutes, int)
        or not 1 <= slot_interval_minutes <= 1440
    ):
        raise ValueError(
            "Slot interval must be between 1 and 1440 minutes."
        )

    if (
        isinstance(max_suggestions, bool)
        or not isinstance(max_suggestions, int)
        or not 1 <= max_suggestions <= 50
    ):
        raise ValueError(
            "Maximum suggestions must be between 1 and 50."
        )

    busy_periods = find_conflicts(start_date, end_date)

    timezone = start_date.tzinfo

    busy = []

    for period in busy_periods:

        busy_start = datetime.fromisoformat(
            period["start"].replace("Z", "+00:00")
        )

        busy_end = datetime.fromisoformat(
            period["end"].replace("Z", "+00:00")
        )

        if busy_start.tzinfo is None:
            busy_start = busy_start.replace(tzinfo=timezone)

        if busy_end.tzinfo is None:
            busy_end = busy_end.replace(tzinfo=timezone)

        busy_start = busy_start.astimezone(timezone)
        busy_end = busy_end.astimezone(timezone)

        # Ignore periods outside the requested range.
        if busy_end <= start_date or busy_start >= end_date:
            continue

        busy_start = max(busy_start, start_date)
        busy_end = min(busy_end, end_date)

        busy.append((busy_start, busy_end))

    busy.sort(key=lambda item: item[0])

    # --------------------------------------------------
    # 1. Identify uninterrupted free windows
    # --------------------------------------------------

    free_windows = []
    cursor = start_date

    for busy_start, busy_end in busy:

        if busy_end <= cursor:
            continue

        if busy_start > cursor:

            free_windows.append(
                (cursor, busy_start)
            )

        cursor = max(cursor, busy_end)

        if cursor >= end_date:
            break

    if cursor < end_date:

        free_windows.append(
            (cursor, end_date)
        )

    # --------------------------------------------------
    # 2. Generate fixed-duration candidate slots
    # --------------------------------------------------

    slots = []

    duration = timedelta(minutes=duration_minutes)
    interval = timedelta(minutes=slot_interval_minutes)

    for window_start, window_end in free_windows:

        candidate_start = window_start

        while candidate_start + duration <= window_end:

            candidate_end = candidate_start + duration

            slots.append({
                "start": candidate_start.isoformat(),
                "end": candidate_end.isoformat(),
            })

            if len(slots) >= max_suggestions:
                return slots

            candidate_start += interval

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