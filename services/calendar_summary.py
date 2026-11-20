from collections import Counter
from datetime import date, datetime, timedelta

from services.event_search import (
    get_event_for_day,
    get_event_for_week,
    get_event_for_month,
)

from utils.datetime_utils import (
    parse_datetime,
    get_week_range,
    get_month_range,
)


def _get_event_dates(
    event: dict,
    range_start: date,
    range_end: date,
) -> list[date]:

    start = event.get("start", {})
    end = event.get("end", {})

    if not start or not end:
        return []

    if "date" in start and "date" in end:

        event_start = date.fromisoformat(start["date"])
        event_end = date.fromisoformat(end["date"])

        first_day = max(event_start, range_start)
        last_day_exclusive = min(event_end, range_end)

        dates = []
        current = first_day

        while current < last_day_exclusive:
            dates.append(current)
            current += timedelta(days=1)

        return dates

    if "dateTime" in start and "dateTime" in end:

        start_dt = parse_datetime(start["dateTime"])
        end_dt = parse_datetime(end["dateTime"])

        if start_dt >= end_dt:
            return []

        first_day = max(start_dt.date(), range_start)

        last_day = min(
            (end_dt - timedelta(microseconds=1)).date(),
            range_end - timedelta(days=1),
        )

        if first_day > last_day:
            return []

        dates = []
        current = first_day

        while current <= last_day:
            dates.append(current)
            current += timedelta(days=1)

        return dates

    return []


async def count_events_in_range(start_date, end_date):
    from services.calendar_service import list_events_in_range

    events = await list_events_in_range(
        start_date,
        end_date,
    )

    return sum(
        1
        for event in events
        if event.get("status") != "cancelled"
    )


async def get_daily_schedule(day: str):

    events = await get_event_for_day(day)

    return {
        "date": day,
        "total_events": len(events),
        "events": events,
    }


async def get_weekly_schedule(week: str | None = None):

    week_start, week_end = get_week_range(week)

    events = await get_event_for_week(week)

    grouped = {}

    for event in events:

        occupied_dates = _get_event_dates(
            event,
            week_start.date(),
            week_end.date(),
        )

        for event_date in occupied_dates:

            key = event_date.isoformat()

            grouped.setdefault(
                key,
                [],
            ).append(event)

    return {
        "total_events": len(events),
        "days": dict(sorted(grouped.items())),
    }


async def get_monthly_overview(month: str | None = None):

    month_start, month_end = get_month_range(month)

    events = await get_event_for_month(month)

    counts = Counter()

    for event in events:

        occupied_dates = _get_event_dates(
            event,
            month_start.date(),
            month_end.date(),
        )

        for event_date in occupied_dates:
            counts[event_date.isoformat()] += 1

    return {
        "total_events": len(events),
        "daily_counts": dict(sorted(counts.items())),
    }


async def get_calendar_summary(
    period: str,
    value: str | None = None,
):
    period = period.lower()

    if period == "day":
        return await get_daily_schedule(
            value or "today"
        )

    if period == "week":
        return await get_weekly_schedule(value)

    if period == "month":
        return await get_monthly_overview(value)

    raise ValueError(
        "Period must be day, week, or month."
    )