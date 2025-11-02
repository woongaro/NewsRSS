from typing import Dict, List

from flask import Flask, Response, jsonify, request, render_template
from flask_cors import CORS
import feedparser
from urllib.parse import quote
import re

DEFAULT_QUERY: str = 'ai'
MAX_QUERY_LENGTH: int = 200

app = Flask(__name__)
CORS(app)  # 프론트엔드에서 API 호출 허용


def _validate_query(raw_query: str | None) -> str:
    """검색어를 검증하고 정제된 문자열을 반환한다.

    Args:
        raw_query: 사용자 요청에서 전달된 원본 검색어.

    Returns:
        공백이 제거되고 길이가 제한된 검색어.

    Raises:
        ValueError: 검색어가 비어 있거나 허용 길이를 초과한 경우.
    """

    # 공백 제거 후 기본 검색어 적용
    if raw_query is None:
        candidate: str = DEFAULT_QUERY
    else:
        candidate = raw_query

    cleaned_query: str = candidate.strip()
    if not cleaned_query:
        raise ValueError('검색어는 최소 1자 이상 입력해야 합니다.')
    if len(cleaned_query) > MAX_QUERY_LENGTH:
        raise ValueError(f'검색어는 {MAX_QUERY_LENGTH}자 이하로 입력해주세요.')
    return cleaned_query


@app.route('/')
def index() -> str:
    """메인 페이지를 렌더링한다."""

    return render_template('index.html')


@app.route('/api/news')
def get_news() -> Response | tuple[Response, int]:
    """뉴스 검색 API 엔드포인트를 처리한다.

    Returns:
        검색 결과 또는 오류 정보를 포함한 JSON 응답.
    """

    try:
        try:
            query: str = _validate_query(request.args.get('q'))
        except ValueError as validation_error:
            app.logger.warning('Invalid query parameter: %s', validation_error)
            return (
                jsonify({
                    'status': 'error',
                    'message': '유효한 검색어를 입력해주세요.',
                }),
                400,
            )

        # 한글 검색어 URL 인코딩
        encoded_query: str = quote(query)
        feed_url: str = (
            f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        )
        feed = feedparser.parse(feed_url)

        news_list: List[Dict[str, str]] = []
        for entry in feed.entries:
            # 이미지 URL 추출
            image_url: str = ''

            # 1. media_content에서 이미지 찾기
            if hasattr(entry, 'media_content'):
                for media in entry.media_content:
                    if media.get('type', '').startswith('image/'):
                        image_url = media.get('url', '')
                        break

            # 2. media_thumbnail에서 이미지 찾기
            if not image_url and hasattr(entry, 'media_thumbnail'):
                if entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get('url', '')

            # 3. enclosures에서 이미지 찾기
            if not image_url and hasattr(entry, 'enclosures'):
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('image/'):
                        image_url = enclosure.get('href', '')
                        break

            # 4. summary HTML에서 img 태그 찾기
            if not image_url and entry.get('summary', ''):
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.summary)
                if img_match:
                    image_url = img_match.group(1)

            news_item: Dict[str, str] = {
                'title': entry.title,
                'link': entry.link,
                'published': entry.get('published', ''),
                'summary': entry.get('summary', ''),
                'source': entry.get('source', {}).get('title', '') if hasattr(entry, 'source') else '',
                'image': image_url,
            }
            news_list.append(news_item)

        return jsonify({
            'status': 'success',
            'query': query,
            'count': len(news_list),
            'news': news_list,
        })

    except Exception:  # pylint: disable=broad-except
        app.logger.exception('Unexpected error occurred while fetching news.')
        return (
            jsonify({
                'status': 'error',
                'message': '뉴스를 가져오는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.',
            }),
            500,
        )

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port) 