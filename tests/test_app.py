"""app 모듈의 뉴스 검색 API에 대한 단위 테스트."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from app import app as flask_app  # noqa: E402


class DummyEntry(dict):
    """feedparser 항목을 모사하기 위한 헬퍼 클래스."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__dict__.update(kwargs)

    def get(self, key: str, default: Any | None = None) -> Any:
        return super().get(key, default)


@pytest.fixture(name='client')
def fixture_client() -> Any:
    """Flask 테스트 클라이언트를 생성한다."""

    flask_app.config['TESTING'] = True
    return flask_app.test_client()


def test_get_news_success(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """정상 검색 시 성공 응답이 반환되는지 검증한다."""

    dummy_entry = DummyEntry(
        title='샘플 뉴스',
        link='https://example.com/news',
        published='2024-01-01',
        summary='<p>요약</p>',
    )
    dummy_entry.media_content = [{'type': 'image/jpeg', 'url': 'https://example.com/image.jpg'}]

    class DummyFeed:
        entries: List[Dict[str, Any]] = [dummy_entry]

    def mock_parse(_: str) -> DummyFeed:
        return DummyFeed()

    monkeypatch.setattr('feedparser.parse', mock_parse)

    response = client.get('/api/news?q=ai')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['status'] == 'success'
    assert payload['query'] == 'ai'
    assert payload['count'] == 1
    assert payload['news'][0]['title'] == '샘플 뉴스'


@pytest.mark.parametrize(
    'query_param',
    ['', '   ', 'a' * 201],
)
def test_get_news_invalid_query_returns_bad_request(
    client: Any, query_param: str
) -> None:
    """유효하지 않은 검색어 입력 시 400 오류가 반환되는지 확인한다."""

    response = client.get('/api/news', query_string={'q': query_param})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload['status'] == 'error'
    assert '유효한 검색어' in payload['message']


def test_get_news_handles_unexpected_error(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """외부 RSS 파싱 중 예외 발생 시 500 오류와 일반 메시지를 반환한다."""

    def mock_parse(_: str) -> None:
        raise RuntimeError('boom')

    monkeypatch.setattr('feedparser.parse', mock_parse)

    response = client.get('/api/news?q=ai')

    assert response.status_code == 500
    payload = response.get_json()
    assert payload['status'] == 'error'
    assert '잠시 후 다시 시도해주세요' in payload['message']
