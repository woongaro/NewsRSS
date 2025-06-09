import feedparser

query = "부정선거"
feed_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
feed = feedparser.parse(feed_url)

for entry in feed.entries:
    print(entry.title, entry.link)