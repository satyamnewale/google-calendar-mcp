
from collections import Counter

from services.event_search import (
    get_event_for_day,
    get_event_for_week,
    get_event_for_month,
)

from services.calendar_service import list_events_in_range


def count_events_in_range(start_date, end_date):
    events = list_events_in_range(start_date, end_date)

    return sum(
        1 for event in events
        if event.get("status") != "cancelled"
    )


def get_daily_schedule(day: str):
    events = get_event_for_day(day)

    return {
        "date": day,
        "total_events": len(events),
        "events": events,
    }


def get_weekly_schedule(week: str | None = None):
    events = get_event_for_week(week)

    grouped = {}

    for event in events:
        start = event.get("start", {})

        event_date = (
            start.get("dateTime", start.get("date", ""))[:10]
        )

        grouped.setdefault(event_date, []).append(event)

    return {
        "total_events": len(events),
        "days": grouped,
    }


def get_monthly_overview(month: str | None = None):
    events = get_event_for_month(month)

    counts = Counter()

    for event in events:
        start = event.get("start", {})
        event_date = start.get(
            "dateTime",
            start.get("date", "")
        )[:10]

        counts[event_date] += 1

    return {
        "total_events": len(events),
        "daily_counts": dict(sorted(counts.items())),
    }


def get_calendar_summary(
    period: str,
    value: str | None = None,
):
    period = period.lower()

    if period == "day":
        return get_daily_schedule(value or "today")

    if period == "week":
        return get_weekly_schedule(value)

    if period == "month":
        return get_monthly_overview(value)

    raise ValueError(
        "Period must be day, week, or month."
    )
