
from unittest.mock import AsyncMock

import pytest

from services import calendar_summary


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_daily_schedule(monkeypatch):
    events = [
        {"id": "1", "summary": "Meeting"},
        {"id": "2", "summary": "Review"},
    ]

    get_events = AsyncMock(return_value=events)
    monkeypatch.setattr(
        calendar_summary,
        "get_event_for_day",
        get_events,
    )

    result = await calendar_summary.get_daily_schedule("2026-11-10")

    assert result == {
        "date": "2026-11-10",
        "total_events": 2,
        "events": events,
    }
    get_events.assert_awaited_once_with("2026-11-10")


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_weekly_schedule(monkeypatch):
    events = [
        {
            "id": "1",
            "summary": "Multi-day event",
            "start": {"date": "2026-11-09"},
            "end": {"date": "2026-11-11"},
        }
    ]

    get_events = AsyncMock(return_value=events)
    monkeypatch.setattr(
        calendar_summary,
        "get_event_for_week",
        get_events,
    )

    result = await calendar_summary.get_weekly_schedule("2026-11-09")

    assert result["total_events"] == 1
    assert result["days"]["2026-11-09"] == events
    assert result["days"]["2026-11-10"] == events
    get_events.assert_awaited_once_with("2026-11-09")


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_monthly_overview(monkeypatch):
    events = [
        {
            "id": "1",
            "summary": "Multi-day event",
            "start": {"date": "2026-11-01"},
            "end": {"date": "2026-11-04"},
        }
    ]

    get_events = AsyncMock(return_value=events)
    monkeypatch.setattr(
        calendar_summary,
        "get_event_for_month",
        get_events,
    )

    result = await calendar_summary.get_monthly_overview("2026-11")

    assert result["total_events"] == 1
    assert result["daily_counts"]["2026-11-01"] == 1
    assert result["daily_counts"]["2026-11-02"] == 1
    assert result["daily_counts"]["2026-11-03"] == 1
    get_events.assert_awaited_once_with("2026-11")


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_calendar_summary_dispatches_to_day(monkeypatch):
    daily = AsyncMock(return_value={"total_events": 1})
    monkeypatch.setattr(calendar_summary, "get_daily_schedule", daily)

    result = await calendar_summary.get_calendar_summary("day", "2026-11-10")

    assert result == {"total_events": 1}
    daily.assert_awaited_once_with("2026-11-10")


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_calendar_summary_dispatches_to_week(monkeypatch):
    weekly = AsyncMock(return_value={"total_events": 2})
    monkeypatch.setattr(calendar_summary, "get_weekly_schedule", weekly)

    result = await calendar_summary.get_calendar_summary("week", "2026-11-09")

    assert result == {"total_events": 2}
    weekly.assert_awaited_once_with("2026-11-09")


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_calendar_summary_dispatches_to_month(monkeypatch):
    monthly = AsyncMock(return_value={"total_events": 3})
    monkeypatch.setattr(calendar_summary, "get_monthly_overview", monthly)

    result = await calendar_summary.get_calendar_summary("month", "2026-11")

    assert result == {"total_events": 3}
    monthly.assert_awaited_once_with("2026-11")


@pytest.mark.asyncio
@pytest.mark.services
async def test_get_calendar_summary_rejects_unknown_period():
    with pytest.raises(ValueError, match="Period must be day, week, or month"):
        await calendar_summary.get_calendar_summary("year", "2026")
