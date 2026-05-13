from datetime import datetime, timezone

from src.cli.main import build_publish_schedule, resolve_schedule_settings


def test_resolve_schedule_settings_uses_defaults_when_enabled():
    schedule_hours, interval_hours = resolve_schedule_settings(
        schedule_hours=None,
        schedule_interval_hours=None,
        schedule_posts_enabled=True,
        default_schedule_hours=1,
        default_schedule_interval_hours=2,
    )

    assert schedule_hours == 1
    assert interval_hours == 2


def test_resolve_schedule_settings_disables_defaults_when_scheduling_off():
    schedule_hours, interval_hours = resolve_schedule_settings(
        schedule_hours=None,
        schedule_interval_hours=None,
        schedule_posts_enabled=False,
        default_schedule_hours=1,
        default_schedule_interval_hours=2,
    )

    assert schedule_hours == 0
    assert interval_hours == 0


def test_build_publish_schedule_returns_staggered_future_dates():
    publish_status, schedule_dates = build_publish_schedule(
        total_posts=3,
        schedule_hours=1,
        schedule_interval_hours=1,
        now=datetime(2026, 5, 11, 8, 0, 0, tzinfo=timezone.utc),
    )

    assert publish_status == "future"
    assert schedule_dates == [
        "2026-05-11T09:00:00+00:00",
        "2026-05-11T10:00:00+00:00",
        "2026-05-11T11:00:00+00:00",
    ]


def test_build_publish_schedule_returns_drafts_when_disabled():
    publish_status, schedule_dates = build_publish_schedule(
        total_posts=2,
        schedule_hours=0,
        schedule_interval_hours=1,
    )

    assert publish_status == "draft"
    assert schedule_dates == [None, None]
