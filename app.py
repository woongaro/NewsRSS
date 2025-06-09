from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import feedparser
from urllib.parse import quote

app = Flask(__name__)
CORS(app)  # 프론트엔드에서 API 호출 허용

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news')
def get_news():
    query = request.args.get('q', 'ai')  # 기본값: ai
    
    try:
        # 한글 검색어 URL 인코딩
        encoded_query = quote(query)
        feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(feed_url)
        
        news_list = []
        for entry in feed.entries:
            # 이미지 URL 추출
            image_url = ''
            
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
                import re
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.summary)
                if img_match:
                    image_url = img_match.group(1)
            
            news_item = {
                'title': entry.title,
                'link': entry.link,
                'published': entry.get('published', ''),
                'summary': entry.get('summary', ''),
                'source': entry.get('source', {}).get('title', '') if hasattr(entry, 'source') else '',
                'image': image_url
            }
            news_list.append(news_item)
        
        return jsonify({
            'status': 'success',
            'query': query,
            'count': len(news_list),
            'news': news_list
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port) 