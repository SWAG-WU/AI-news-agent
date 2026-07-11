from datetime import datetime

from src.storage import Article, SQLiteStorage


def test_add_preserves_sent_state_when_article_was_already_sent(tmp_path):
    storage = SQLiteStorage(str(tmp_path / "history.db"))
    sent_at = datetime(2026, 1, 2, 3, 4, 5)

    added = storage.add(
        {
            "url": "https://example.com/article",
            "title": "A shipped article",
            "description": "Already delivered to the chat",
            "summary": "Already delivered.",
            "is_sent": True,
            "sent_at": sent_at.isoformat(),
        }
    )

    assert added is True
    session = storage.get_session()
    try:
        article = session.query(Article).one()
        assert article.is_sent is True
        assert article.sent_at == sent_at
    finally:
        session.close()
