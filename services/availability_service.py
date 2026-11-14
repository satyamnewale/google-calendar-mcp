from datetime import datetime, timedelta, time as datetime_time

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
        "items": [{"id": calendar_id}],
    }

    response = service.freebusy().query(body=body).execute()

    calendar_data = response.get("calendars", {}).get(calendar_id, {})
    errors = calendar_data.get("errors", [])

    if errors:
        raise RuntimeError(f"Google FreeBusy API returned errors: {errors}")

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


def _free_windows_for_period(
    window_start: datetime,
    window_end: datetime,
    busy_periods: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    """Subtract busy intervals and return free windows in time order."""

    free_windows = []
    cursor = window_start

    for busy_start, busy_end in busy_periods:

        if busy_end <= cursor:
            continue

        if busy_start >= window_end:
            break

        if busy_start > cursor:
            free_windows.append(
                (
                    cursor,
                    min(busy_start, window_end),
                )
            )

        cursor = max(cursor, busy_end)

        if cursor >= window_end:
            break

    if cursor < window_end:
        free_windows.append(
            (
                cursor,
                window_end,
            )
        )

    return free_windows


def _build_search_windows(
    start_date: datetime,
    end_date: datetime,
    timezone,
    workday_start: datetime_time | None,
    workday_end: datetime_time | None,
    exclude_weekends: bool,
) -> list[tuple[datetime, datetime]]:
    """
    Build search windows, clipped to the requested range.

    With no working hours and no weekend exclusion, search the full
    supplied interval. With weekend exclusion, split it by local date
    so weekend dates can be skipped without requiring business hours.
    """

    if workday_start is None and not exclude_weekends:
        return [(start_date, end_date)]

    windows = []
    current_day = start_date.date()
    final_day = end_date.date()

    while current_day <= final_day:

        if exclude_weekends and current_day.weekday() >= 5:
            current_day += timedelta(days=1)
            continue

        if workday_start is None:
            # Full local calendar day. Construct the next midnight
            # separately so this also handles timezone transitions.
            daily_start = datetime.combine(
                current_day,
                datetime_time.min,
                tzinfo=timezone,
            )
            daily_end = datetime.combine(
                current_day + timedelta(days=1),
                datetime_time.min,
                tzinfo=timezone,
            )
        else:
            daily_start = datetime.combine(
                current_day,
                workday_start,
                tzinfo=timezone,
            )
            daily_end = datetime.combine(
                current_day,
                workday_end,
                tzinfo=timezone,
            )

        daily_start = max(daily_start, start_date)
        daily_end = min(daily_end, end_date)

        if daily_start < daily_end:
            windows.append((daily_start, daily_end))

        current_day += timedelta(days=1)

    return windows


def get_available_slots(
    start_date: datetime,
    end_date: datetime,
    duration_minutes: int = 60,
    slot_interval_minutes: int = 15,
    max_suggestions: int = 10,
    workday_start_time: str | None = None,
    workday_end_time: str | None = None,
    exclude_weekends: bool = False,
):
    """
    Generate exact-duration free slots in chronological order.

    The end boundary is exclusive. When weekend exclusion is enabled
    without working hours, the full weekday portions of the interval
    are searched.
    """

    validate_time_range(start_date, end_date)

    if start_date.tzinfo is None or end_date.tzinfo is None:
        raise ValueError("Start and end datetimes must include timezone information.")

    if (
        isinstance(duration_minutes, bool)
        or not isinstance(duration_minutes, int)
        or not 1 <= duration_minutes <= 1440
    ):
        raise ValueError("Duration must be an integer between 1 and 1440 minutes.")

    if (
        isinstance(slot_interval_minutes, bool)
        or not isinstance(slot_interval_minutes, int)
        or not 1 <= slot_interval_minutes <= 1440
    ):
        raise ValueError("Slot interval must be an integer between 1 and 1440 minutes.")

    if (
        isinstance(max_suggestions, bool)
        or not isinstance(max_suggestions, int)
        or not 1 <= max_suggestions <= 50
    ):
        raise ValueError("Maximum suggestions must be an integer between 1 and 50.")

    if (workday_start_time is None) != (workday_end_time is None):
        raise ValueError("Provide both workday_start_time and workday_end_time.")

    workday_start = None
    workday_end = None

    if workday_start_time is not None:

        try:
            workday_start = datetime_time.fromisoformat(workday_start_time)
            workday_end = datetime_time.fromisoformat(workday_end_time)

        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Working-hours times must use valid HH:MM values."
            ) from exc

        if (
            len(workday_start_time) != 5
            or len(workday_end_time) != 5
            or workday_start.second != 0
            or workday_end.second != 0
            or workday_start.tzinfo is not None
            or workday_end.tzinfo is not None
        ):
            raise ValueError("Working-hours times must use HH:MM format.")

        if workday_end <= workday_start:
            raise ValueError("Working-hours end must be later than start.")

    busy_periods = find_conflicts(start_date, end_date)
    timezone = start_date.tzinfo
    busy = []

    for period in busy_periods:

        busy_start = datetime.fromisoformat(period["start"].replace("Z", "+00:00"))
        busy_end = datetime.fromisoformat(period["end"].replace("Z", "+00:00"))

        if busy_start.tzinfo is None:
            busy_start = busy_start.replace(tzinfo=timezone)
        else:
            busy_start = busy_start.astimezone(timezone)

        if busy_end.tzinfo is None:
            busy_end = busy_end.replace(tzinfo=timezone)
        else:
            busy_end = busy_end.astimezone(timezone)

        if busy_end <= start_date or busy_start >= end_date:
            continue

        busy_start = max(busy_start, start_date)
        busy_end = min(busy_end, end_date)

        busy.append((busy_start, busy_end))

    busy.sort(key=lambda item: item[0])

    search_windows = _build_search_windows(
        start_date=start_date,
        end_date=end_date,
        timezone=timezone,
        workday_start=workday_start,
        workday_end=workday_end,
        exclude_weekends=exclude_weekends,
    )

    duration = timedelta(minutes=duration_minutes)
    interval = timedelta(minutes=slot_interval_minutes)
    slots = []

    for window_start, window_end in search_windows:

        free_windows = _free_windows_for_period(
            window_start,
            window_end,
            busy,
        )

        for free_start, free_end in free_windows:

            candidate_start = free_start

            while candidate_start + duration <= free_end:

                candidate_end = candidate_start + duration

                slots.append(
                    {
                        "start": candidate_start.isoformat(),
                        "end": candidate_end.isoformat(),
                    }
                )

                if len(slots) >= max_suggestions:
                    return slots

                candidate_start += interval

    return slots


def find_occurrence_conflicts(
    occurrences: list[tuple[datetime, datetime]],
    busy_periods: list[dict],
) -> list[dict]:
    """
    Compare event occurrences against busy periods.

    Two intervals overlap when:

        occurrence_start < busy_end
        and
        occurrence_end > busy_start
    """

    conflicts = []

    for occurrence_start, occurrence_end in occurrences:

        for busy_period in busy_periods:

            busy_start = datetime.fromisoformat(
                busy_period["start"].replace("Z", "+00:00")
            )
            busy_end = datetime.fromisoformat(busy_period["end"].replace("Z", "+00:00"))

            if occurrence_start < busy_end and occurrence_end > busy_start:
                conflicts.append(
                    {
                        "occurrence": {
                            "start": occurrence_start.isoformat(),
                            "end": occurrence_end.isoformat(),
                        },
                        "existing_event": {
                            "start": busy_start.isoformat(),
                            "end": busy_end.isoformat(),
                        },
                    }
                )

    return conflicts
