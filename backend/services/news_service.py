"""
新闻服务 - Mock 实现 + RSS 真实数据源实现
"""

import logging
import hashlib
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

# 国内时区 UTC+8
TZ_CHINA = timezone(timedelta(hours=8))


# ============================================================
# Mock 新闻服务
# ============================================================

class MockNewsService:
    """使用内置 mock 数据"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def get_categories(self) -> list[dict]:
        from api.data import news_categories
        return news_categories

    async def get_articles(
        self, category: str = "all", keyword: str = "",
        sort: str = "latest", page: int = 1, page_size: int = 10
    ) -> dict:
        from api.data import news_articles
        articles = list(news_articles)

        if category and category != "all":
            articles = [a for a in articles if a["category"] == category]
        if keyword:
            kw = keyword.lower()
            articles = [
                a for a in articles
                if kw in a["title"].lower() or kw in a["summary"].lower()
                or any(kw in t.lower() for t in a.get("tags", []))
            ]
        if sort == "latest":
            articles.sort(key=lambda a: a["published_at"], reverse=True)
        elif sort == "popular":
            articles.sort(key=lambda a: a["read_count"], reverse=True)
        elif sort == "trending":
            articles.sort(key=lambda a: (a["trending"], a["read_count"]), reverse=True)

        total = len(articles)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "articles": articles[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total,
        }

    async def get_trending(self) -> dict:
        from api.data import news_articles
        trending = [a for a in news_articles if a["trending"]][:5]
        tag_counts: dict[str, int] = {}
        for a in news_articles:
            for tag in a.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            "trending_articles": trending,
            "hot_tags": [{"name": t[0], "count": t[1]} for t in top_tags],
        }


# ============================================================
# RSS 新闻服务
# ============================================================

# 默认中文 RSS 源
DEFAULT_RSS_SOURCES = [
    {"url": "https://sspai.com/feed", "category": "tech"},
    {"url": "https://www.36kr.com/feed", "category": "tech"},
    {"url": "http://www.people.com.cn/rss/opinion.xml", "category": "local"},
]

# 分类名映射
CATEGORY_NAMES = {
    "all": {"id": "all", "name": "推荐", "icon": "⭐"},
    "local": {"id": "local", "name": "本地", "icon": "📍"},
    "tech": {"id": "tech", "name": "科技", "icon": "💻"},
    "finance": {"id": "finance", "name": "财经", "icon": "📈"},
    "life": {"id": "life", "name": "生活", "icon": "🏠"},
    "health": {"id": "health", "name": "健康", "icon": "❤️"},
}


class RssNewsService:
    """RSS 聚合新闻服务 - 从多个 RSS 源抓取真实新闻"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        raw_sources = self.config.get("rss", {}).get("sources", [])
        self.sources = raw_sources if raw_sources else DEFAULT_RSS_SOURCES
        self._cache: dict | None = None
        self._cache_time: datetime | None = None
        self._cache_ttl = self.config.get("rss", {}).get("cache_ttl", 300)  # 5分钟

    async def _fetch_all_articles(self) -> list[dict]:
        """抓取所有 RSS 源并返回统一格式的文章列表"""
        import feedparser
        import httpx

        articles = []
        article_id = 0

        for source in self.sources:
            url = source["url"]
            category = source.get("category", "tech")
            try:
                async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Linux; Android 14) "
                                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
                    }
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)

                for entry in feed.entries[:20]:  # 每个源最多20条
                    article_id += 1
                    published = entry.get("published_parsed") or entry.get("updated_parsed")
                    if published:
                        pub_time = datetime(*published[:6], tzinfo=timezone.utc).astimezone(TZ_CHINA)
                        pub_str = pub_time.strftime("%Y-%m-%dT%H:%M:%S")
                    else:
                        pub_str = datetime.now(TZ_CHINA).strftime("%Y-%m-%dT%H:%M:%S")

                    # 提取标签
                    tags = []
                    if entry.get("tags"):
                        for t in entry.tags[:5]:
                            tag_name = t.get("term", "") if isinstance(t, dict) else str(t)
                            if tag_name and len(tag_name) < 10:
                                tags.append(tag_name)
                    if category:
                        tags.insert(0, category)

                    # 用 URL 哈希作为 ID
                    eid = hashlib.md5(entry.get("link", str(article_id)).encode()).hexdigest()[:8]

                    articles.append({
                        "id": int(eid, 16) % 100000,
                        "category": category,
                        "title": entry.get("title", "无标题"),
                        "summary": _clean_summary(entry.get("summary", entry.get("description", ""))),
                        "source": entry.get("source", {}).get("title", feed.feed.get("title", source["url"])),
                        "author": entry.get("author", "未知"),
                        "published_at": pub_str,
                        "image": _category_icon(category),
                        "tags": tags,
                        "read_count": 0,
                        "trending": False,
                    })
            except Exception as e:
                log.warning(f"RSS 源抓取失败 {url}: {e}")
                continue

        # 按发布时间排序
        articles.sort(key=lambda a: a["published_at"], reverse=True)
        # 前3篇标记为 trending
        for a in articles[:3]:
            a["trending"] = True

        return articles

    async def _get_cached_articles(self) -> list[dict]:
        """带缓存的文章获取"""
        now = datetime.now()
        if self._cache and self._cache_time:
            if (now - self._cache_time).total_seconds() < self._cache_ttl:
                return self._cache
        articles = await self._fetch_all_articles()
        self._cache = articles
        self._cache_time = now
        return articles

    async def get_categories(self) -> list[dict]:
        return list(CATEGORY_NAMES.values())

    async def get_articles(
        self, category: str = "all", keyword: str = "",
        sort: str = "latest", page: int = 1, page_size: int = 10
    ) -> dict:
        try:
            articles = await self._get_cached_articles()
        except Exception as e:
            log.warning(f"RSS 新闻服务失败，回退到 mock: {e}")
            return await MockNewsService().get_articles(category, keyword, sort, page, page_size)

        if category and category != "all":
            articles = [a for a in articles if a["category"] == category]
        if keyword:
            kw = keyword.lower()
            articles = [
                a for a in articles
                if kw in a["title"].lower() or kw in a["summary"].lower()
                or any(kw in t.lower() for t in a.get("tags", []))
            ]
        if sort == "latest":
            articles.sort(key=lambda a: a["published_at"], reverse=True)
        elif sort == "popular":
            articles.sort(key=lambda a: a["read_count"], reverse=True)
        elif sort == "trending":
            articles.sort(key=lambda a: (a["trending"], a["read_count"]), reverse=True)

        total = len(articles)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "articles": articles[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total,
        }

    async def get_trending(self) -> dict:
        try:
            articles = await self._get_cached_articles()
        except Exception:
            return await MockNewsService().get_trending()

        trending = [a for a in articles if a["trending"]][:5]
        tag_counts: dict[str, int] = {}
        for a in articles:
            for tag in a.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            "trending_articles": trending,
            "hot_tags": [{"name": t[0], "count": t[1]} for t in top_tags],
        }


def _clean_summary(html_text: str) -> str:
    """清理 HTML，提取纯文本摘要"""
    import re
    text = re.sub(r"<[^>]+>", "", html_text or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 300:
        text = text[:300] + "..."
    return text


def _category_icon(cat: str) -> str:
    icons = {"local": "📍", "tech": "💻", "finance": "📈", "life": "🏠", "health": "❤️"}
    return icons.get(cat, "📰")
