from datetime import datetime, timezone

from src.cli.main import (
    build_publish_schedule,
    build_work_items,
    resolve_schedule_settings,
)


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


def test_build_work_items_keeps_plan_items_and_appends_ordinary_keywords():
    filtered_keywords = [
        "lighting hardware manufacturer",
        "lighting hardware sourcing guide",
        "wall lamp parts supplier",
    ]
    keyword_categories = {
        "lighting hardware manufacturer": "Technical Guides",
        "lighting hardware sourcing guide": "Industry Insights",
        "wall lamp parts supplier": "Technical Guides",
    }
    keyword_metadata = {
        "lighting hardware manufacturer": {
            "keyword": "lighting hardware manufacturer",
            "category": "Technical Guides",
            "lane": "pillar",
            "priority": "A",
            "cluster": "core",
            "internal_link_targets": "Home; Services",
        },
        "lighting hardware sourcing guide": {
            "keyword": "lighting hardware sourcing guide",
            "category": "Industry Insights",
            "lane": "ordinary",
            "priority": "A",
            "cluster": "procurement",
            "internal_link_targets": "Services; Contact",
        },
        "wall lamp parts supplier": {
            "keyword": "wall lamp parts supplier",
            "category": "Technical Guides",
            "lane": "ordinary",
            "priority": "B",
            "cluster": "wall",
            "internal_link_targets": "Wall Lamp Sets; Services",
        },
    }
    plan_rows = [
        {
            "keyword": "lighting hardware manufacturer",
            "category": "Technical Guides",
            "lane": "pillar",
            "priority": "A",
            "cluster": "core",
            "direction": "supplier comparison",
            "title_angle": "supplier comparison",
            "internal_link_targets": "Home; Services",
        }
    ]

    items = build_work_items(
        filtered_keywords,
        keyword_categories,
        keyword_metadata=keyword_metadata,
        ordered_keywords=[
            "lighting hardware manufacturer",
            "lighting hardware sourcing guide",
            "wall lamp parts supplier",
        ],
        plan_rows=plan_rows,
    )

    assert [item["keyword"] for item in items] == [
        "lighting hardware manufacturer",
        "lighting hardware sourcing guide",
        "wall lamp parts supplier",
    ]
    assert items[0]["direction"] == "supplier comparison"
    assert items[1]["lane"] == "ordinary"
    assert items[1]["priority"] == "A"
    assert items[2]["priority"] == "B"


def test_build_work_items_does_not_duplicate_planned_keyword_in_ordinary_queue():
    items = build_work_items(
        ["lighting hardware manufacturer"],
        {"lighting hardware manufacturer": "Technical Guides"},
        keyword_metadata={
            "lighting hardware manufacturer": {
                "keyword": "lighting hardware manufacturer",
                "category": "Technical Guides",
                "lane": "ordinary",
                "priority": "A",
                "cluster": "core",
                "internal_link_targets": "Home",
            }
        },
        ordered_keywords=["lighting hardware manufacturer"],
        plan_rows=[
            {
                "keyword": "lighting hardware manufacturer",
                "category": "Technical Guides",
                "lane": "pillar",
                "priority": "A",
                "cluster": "core",
                "direction": "factory overview",
                "title_angle": "factory overview",
                "internal_link_targets": "Home",
            }
        ],
    )

    assert len(items) == 1
    assert items[0]["lane"] == "pillar"
