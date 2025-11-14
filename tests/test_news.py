"""`news` 모듈 단위 테스트."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import news


class DummyFeed:
    """feedparser.parse가 반환하는 객체를 모사한다."""

    def __init__(self, *, entries: List[Any], bozo: bool = False, bozo_exception: Exception | None = None) -> None:
        self.entries = entries
        self.bozo = bozo
        self.bozo_exception = bozo_exception


def _make_entry(data: Dict[str, Any]) -> SimpleNamespace:
    """feedparser의 FeedParserDict와 유사한 객체를 만든다."""

    return SimpleNamespace(**data)


def test_fetch_news_returns_articles(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상적인 피드에서 뉴스 목록을 반환한다."""

    entries = [
        _make_entry(
            {
                "title": "테스트 뉴스",
                "link": "https://example.com/article",
                "published": "2024-01-01",
                "summary": "<p>요약</p>",
                "source": {"title": "Example"},
                "media_content": [{"type": "image/png", "url": "https://example.com/image.png"}],
            }
        )
    ]

    monkeypatch.setattr(news.feedparser, "parse", lambda _: DummyFeed(entries=entries))

    articles = news.fetch_news("test")

    assert len(articles) == 1
    article = articles[0]
    assert article.title == "테스트 뉴스"
    assert article.link == "https://example.com/article"
    assert article.published == "2024-01-01"
    assert article.summary == "<p>요약</p>"
    assert article.source == "Example"
    assert article.image == "https://example.com/image.png"


def test_fetch_news_raises_on_empty_query() -> None:
    """빈 검색어가 주어지면 ValueError를 발생시킨다."""

    with pytest.raises(ValueError):
        news.fetch_news("   ")


def test_fetch_news_raises_on_bozo(monkeypatch: pytest.MonkeyPatch) -> None:
    """RSS 파싱 오류(bozo)가 발생하면 RuntimeError를 발생시킨다."""

    dummy_exception = RuntimeError("파싱 실패")
    monkeypatch.setattr(
        news.feedparser,
        "parse",
        lambda _: DummyFeed(entries=[], bozo=True, bozo_exception=dummy_exception),
    )

    with pytest.raises(RuntimeError) as exc_info:
        news.fetch_news("test")

    assert "RSS 피드를 파싱" in str(exc_info.value)

