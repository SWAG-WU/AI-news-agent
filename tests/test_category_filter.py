from datetime import datetime, timedelta

from src.filters.category_filter import CategoryFilter


class _CategoryFilterConfig:
    enabled = True
    min_target_count = 10
    max_target_count = 10
    academic_min_count = 1
    academic_max_count = 3
    media_min_count = 2
    latest_count = 3
    new_model_extra_count = 0
    new_model_hours = 48
    fun_github_extra_count = 0
    dual_channel_mode = False
    tools_channel_count = 3
    academic_media_channel_count = 10


class _Thresholds:
    category_filter = _CategoryFilterConfig()


class _Config:
    thresholds = _Thresholds()


def _article(index, category="media", score=1):
    published_at = datetime(2026, 1, 1) + timedelta(minutes=index)
    return {
        "url": f"https://example.com/{index}",
        "title": f"AI article {index}",
        "description": "A detailed AI article",
        "published_at": published_at.isoformat(),
        "source": "Example",
        "category": category,
        "score": score,
    }


def test_single_channel_output_respects_configured_max_target_count():
    articles = [_article(i) for i in range(20)]
    filter_obj = CategoryFilter(_Config())

    result = filter_obj.filter_for_daily_output(articles)
    regular = [a for a in result if not a.get("is_extra")]

    assert len(regular) <= _CategoryFilterConfig.max_target_count


def test_recency_and_score_sort_uses_higher_score_for_same_timestamp():
    filter_obj = CategoryFilter(_Config())
    same_time = "2026-01-01T00:00:00"
    articles = [
        {**_article(1, score=1), "published_at": same_time},
        {**_article(2, score=9), "published_at": same_time},
    ]

    result = filter_obj._sort_articles_by_recency_and_score(articles)

    assert result[0]["score"] == 9
