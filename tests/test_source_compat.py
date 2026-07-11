from src.collectors.blog_collector import BlogCollector
from src.config import get_config


def test_blog_collector_uses_compatible_source_name_for_new_source_config():
    config = get_config()
    source = next(s for s in config.sources.sources if s._id == "openai_blog")
    collector = BlogCollector(config)

    article = collector._parse_entry(
        {
            "title": "New model release",
            "link": "/blog/new-model",
            "description": "AI model release details",
            "published": "2026-01-01T00:00:00Z",
        },
        source,
    )

    assert article["source"] == source._name
