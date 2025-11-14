"""Google 뉴스 RSS 검색 유틸리티 모듈.

이 모듈은 Google 뉴스 RSS 피드에서 특정 검색어에 대한 기사 목록을 가져오는
도우미 함수를 제공한다. 모든 함수와 클래스는 유지보수를 고려해 타입 힌트를
포함하며, 예외 상황을 명확하게 처리한다.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, List
from urllib.parse import quote

import feedparser


logger = logging.getLogger(__name__)


DEFAULT_QUERY: str = "ai"
DEFAULT_LANGUAGE: str = "ko"
DEFAULT_REGION: str = "KR"


@dataclass(slots=True)
class NewsArticle:
    """RSS 항목을 표현하는 데이터 구조.

    Attributes:
        title: 기사 제목.
        link: 기사 원문 URL.
        published: 게시 시각 정보(존재하지 않을 경우 ``None``).
        summary: 기사 요약(존재하지 않을 경우 ``None``).
        source: 기사 출처(존재하지 않을 경우 ``None``).
        image: 대표 이미지 URL(확인되지 않으면 ``None``).
    """

    title: str
    link: str
    published: str | None = None
    summary: str | None = None
    source: str | None = None
    image: str | None = None


def _clean_query(query: str | None) -> str:
    """검색어를 정제하고 검증한다.

    Args:
        query: 사용자가 입력한 검색어. ``None``이면 기본 검색어를 사용한다.

    Returns:
        공백이 제거된 검증된 검색어 문자열.

    Raises:
        ValueError: 검색어가 비어 있는 경우.
    """

    candidate: str = (query or DEFAULT_QUERY).strip()
    if not candidate:
        raise ValueError("검색어는 최소 1자 이상 입력해야 합니다.")
    return candidate


def _get_entry_value(entry: Any, key: str) -> Any:
    """엔트리에서 키에 해당하는 값을 추출한다.

    Args:
        entry: RSS 엔트리 객체.
        key: 추출하려는 필드명.

    Returns:
        키에 해당하는 값. 존재하지 않으면 ``None``.
    """

    if hasattr(entry, "get"):
        return entry.get(key)
    return getattr(entry, key, None)


def _extract_image(entry: Any) -> str | None:
    """RSS 엔트리에서 이미지 URL을 추출한다.

    Args:
        entry: feedparser가 반환한 RSS 엔트리 객체.

    Returns:
        추출된 이미지 URL. 이미지가 없으면 ``None``.
    """

    media_content = _get_entry_value(entry, "media_content") or []
    for media in media_content:
        media_type: str = media.get("type", "")
        if media_type.startswith("image/"):
            return media.get("url")

    media_thumbnail = _get_entry_value(entry, "media_thumbnail") or []
    if media_thumbnail:
        return media_thumbnail[0].get("url")

    enclosures = _get_entry_value(entry, "enclosures") or []
    for enclosure in enclosures:
        enclosure_type: str = enclosure.get("type", "")
        if enclosure_type.startswith("image/"):
            return enclosure.get("href")

    summary: str | None = _get_entry_value(entry, "summary")
    if summary:
        match = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"']", summary)
        if match:
            return match.group(1)

    return None


def _build_feed_url(query: str, language: str, region: str) -> str:
    """Google 뉴스 RSS URL을 생성한다.

    Args:
        query: 검색어 문자열.
        language: Google 뉴스 언어 코드.
        region: Google 뉴스 지역 코드.

    Returns:
        완성된 RSS 피드 URL.
    """

    encoded_query: str = quote(query)
    return f"https://news.google.com/rss/search?q={encoded_query}&hl={language}&gl={region}&ceid={region}:{language}"


def _convert_entries(entries: Iterable[Any]) -> List[NewsArticle]:
    """feedparser 엔트리를 `NewsArticle` 목록으로 변환한다.

    Args:
        entries: feedparser가 반환한 엔트리 반복자.

    Returns:
        `NewsArticle` 객체 목록.
    """

    articles: List[NewsArticle] = []
    for entry in entries:
        title: str = _get_entry_value(entry, "title") or ""
        link: str = _get_entry_value(entry, "link") or ""
        published: str | None = _get_entry_value(entry, "published")
        summary: str | None = _get_entry_value(entry, "summary")
        source_info: Any = _get_entry_value(entry, "source")
        if isinstance(source_info, dict):
            source_title = source_info.get("title")
        else:
            source_title = getattr(source_info, "title", None)

        article = NewsArticle(
            title=title,
            link=link,
            published=published,
            summary=summary,
            source=source_title,
            image=_extract_image(entry),
        )
        articles.append(article)
    return articles


def fetch_news(
    query: str | None = None,
    *,
    language: str = DEFAULT_LANGUAGE,
    region: str = DEFAULT_REGION,
) -> List[NewsArticle]:
    """Google 뉴스에서 검색 결과를 가져온다.

    Args:
        query: 검색어. ``None``이면 기본 검색어를 사용한다.
        language: Google 뉴스 언어 코드(기본: ``ko``).
        region: Google 뉴스 지역 코드(기본: ``KR``).

    Returns:
        `NewsArticle` 인스턴스 목록.

    Raises:
        ValueError: 검색어가 비어 있는 경우.
        RuntimeError: 피드 파싱 중 예기치 못한 오류가 발생한 경우.
    """

    cleaned_query: str = _clean_query(query)
    feed_url: str = _build_feed_url(cleaned_query, language, region)

    logger.debug("Fetching RSS feed: %s", feed_url)
    feed = feedparser.parse(feed_url)

    if getattr(feed, "bozo", False):
        bozo_exception: Exception | None = getattr(feed, "bozo_exception", None)
        logger.error("RSS 피드 파싱 오류: %s", bozo_exception)
        if isinstance(bozo_exception, Exception):
            raise RuntimeError("RSS 피드를 파싱하는 중 오류가 발생했습니다.") from bozo_exception
        raise RuntimeError("RSS 피드를 파싱하는 중 오류가 발생했습니다.")

    entries: Iterable[Any] = getattr(feed, "entries", [])
    return _convert_entries(entries)


def _configure_logging(verbose: bool) -> None:
    """로깅을 설정한다.

    Args:
        verbose: 디버그 로그 사용 여부.
    """

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s:%(name)s:%(message)s")


def _parse_args() -> argparse.Namespace:
    """CLI 인자를 파싱한다.

    Returns:
        파싱된 명령행 인자를 담은 네임스페이스.
    """

    parser = argparse.ArgumentParser(description="Google 뉴스 RSS 검색 도구")
    parser.add_argument("query", nargs="?", default=None, help="검색어 (기본: ai)")
    parser.add_argument("--language", "-l", default=DEFAULT_LANGUAGE, help="언어 코드 (기본: ko)")
    parser.add_argument("--region", "-r", default=DEFAULT_REGION, help="지역 코드 (기본: KR)")
    parser.add_argument("--verbose", "-v", action="store_true", help="디버그 로그 출력")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="출력할 기사 수 제한",
    )
    return parser.parse_args()


def main() -> None:
    """CLI 진입점.

    Raises:
        SystemExit: 입력 오류 또는 RSS 파싱 오류가 발생한 경우.
    """

    args = _parse_args()
    _configure_logging(args.verbose)

    try:
        articles = fetch_news(args.query, language=args.language, region=args.region)
    except ValueError as validation_error:
        logger.error("입력 오류: %s", validation_error)
        raise SystemExit(1) from validation_error
    except RuntimeError as runtime_error:
        logger.error("뉴스를 가져오는 중 문제가 발생했습니다: %s", runtime_error)
        raise SystemExit(2) from runtime_error

    serialized_articles = [asdict(article) for article in articles]
    if args.limit is not None:
        serialized_articles = serialized_articles[: args.limit]

    output = {
        "query": args.query or DEFAULT_QUERY,
        "count": len(serialized_articles),
        "articles": serialized_articles,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

