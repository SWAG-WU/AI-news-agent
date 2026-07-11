from datetime import datetime, timedelta, timezone

from src.filters.threshold_filter import ThresholdFilter


class _Thresholds:
    class time:
        primary_window_hours = 24

    class content:
        min_title_length = 1
        max_title_length = 200
        min_description_length = 1

    class scoring:
        min_score = 0.0
        weights = {}

    class github:
        stars = None

    class huggingface:
        min_likes = 0
        min_downloads = 0


class _Keywords:
    def get_all_keywords(self):
        return ["AI"]


class _Config:
    thresholds = _Thresholds()
    keywords = _Keywords()


def test_time_window_filters_old_timezone_aware_rss_dates():
    filter_obj = ThresholdFilter(_Config())
    old_dt = datetime.now(timezone.utc) - timedelta(hours=30)
    published_at = old_dt.strftime("%a, %d %b %Y %H:%M:%S %z")

    assert filter_obj._within_time_window({"published_at": published_at}) is False
