"""
新闻服务 - Mock 实现 + RSS 真实数据源实现
"""

import logging
import hashlib
import asyncio
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

# 分类名映射（id -> 显示名/图标）。未知分类会按 id 兜底生成。
CATEGORY_NAMES = {
    "all": {"id": "all", "name": "推荐", "icon": "⭐"},
    "local": {"id": "local", "name": "本地", "icon": "📍"},
    "tech": {"id": "tech", "name": "科技", "icon": "💻"},
    "news": {"id": "news", "name": "综合", "icon": "📰"},
    "intl": {"id": "intl", "name": "国际", "icon": "🌍"},
    "dev": {"id": "dev", "name": "开发者", "icon": "🛠️"},
    "finance": {"id": "finance", "name": "财经", "icon": "📈"},
    "life": {"id": "life", "name": "生活", "icon": "🏠"},
    "health": {"id": "health", "name": "健康", "icon": "❤️"},
}


class RssNewsService:
    """RSS 聚合新闻服务 - 从多个 RSS 源抓取真实新闻"""

    # 国内常见域名（用于来源国内/国外分组）
    _DOMESTIC_DOMAINS = {
        "sspai.com", "36kr.com", "pingwest.com", "ifanr.com", "geekpark.net",
        "tmtpost.com", "leiphone.com", "qbitai.com", "infoq.cn", "ruanyifeng.com",
        "v2ex.com", "people.com.cn", "huxiu.com", "thepaper.cn",
        "zhihu.com", "wallstreetcn.com", "smzdm.com", "douban.com",
        "guokr.com", "economist.com", "zaobao.com.sg",
    }

    @staticmethod
    def _region_of(url: str) -> str:
        """根据 URL 域名判断来源所属区域：domestic（国内）/ foreign（国外）"""
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower()
        except Exception:
            host = url.lower()
        if ".cn" in host:
            return "domestic"
        for d in RssNewsService._DOMESTIC_DOMAINS:
            if d in host:
                return "domestic"
        return "foreign"

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        rss_cfg = self.config.get("rss", {})
        raw_sources = rss_cfg.get("sources", [])
        self.sources = raw_sources if raw_sources else DEFAULT_RSS_SOURCES
        # RSSHub 基础地址：源 URL 可用 rsshub:// 前缀引用，切换实例只改此处一处
        rsshub_base = (rss_cfg.get("rsshub_base") or "").rstrip("/")
        for src in self.sources:
            url = src.get("url", "")
            if rsshub_base and url.startswith("rsshub://"):
                # rsshub://huxiu/article -> {rsshub_base}/huxiu/article
                src["url"] = rsshub_base + "/" + url[len("rsshub://"):]
            # 为每个源预计算区域，便于文章与来源列表分组
            src.setdefault("region", self._region_of(src.get("url", "")))
        self._cache: dict | None = None
        self._cache_time: datetime | None = None
        self._cache_ttl = rss_cfg.get("cache_ttl", 300)  # 5分钟

    # 单源网络超时（秒）。原 8s 偏长：N 个源并发时总耗时 = 最慢那一个，
    # 压到 5s 既给足正常响应时间，又避免个别源卡死把首屏拖到 8s。
    _SOURCE_TIMEOUT = 5.0
    # 单源响应体解析上限（秒）。feedparser 解析不联网，但若某源返回超大 /
    # 畸形 XML，CPU 解析可能长时间挂起，用 wait_for 兜底。
    _PARSE_TIMEOUT = 5.0

    async def _fetch_one_source(self, client: "httpx.AsyncClient", source: dict) -> list[dict]:
        """抓取单个 RSS 源（异常由调用方处理，单源失败不影响整体）"""
        import feedparser

        url = source["url"]
        category = source.get("category", "tech")
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        }
        try:
            resp = await client.get(url, headers=headers, timeout=self._SOURCE_TIMEOUT)
            resp.raise_for_status()
            # 解析本身不联网，但用 wait_for 防止超大/畸形响应体长时间占 CPU
            feed = await asyncio.wait_for(
                asyncio.to_thread(feedparser.parse, resp.text),
                timeout=self._PARSE_TIMEOUT,
            )
        except Exception as e:
            log.warning(f"RSS 源抓取失败 {url}: {e}")
            return []

        results = []
        for entry in feed.entries[:20]:  # 每个源最多20条
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

            # 用 URL 的完整 md5 作为稳定 ID。
            # 旧实现取前 8 位再 % 100000，空间仅 10 万，几百条文章即有可观碰撞概率
            # （生日悖论下 ~600 条时碰撞概率已超 80%），会导致前端 key 重复、
            # 反馈埋点张冠李戴。改为 32 位十六进制全串，实际无碰撞风险。
            link_for_id = entry.get("link") or f"{url}#{len(results)}"
            eid = hashlib.md5(link_for_id.encode("utf-8")).hexdigest()

            results.append({
                "id": eid,
                "category": category,
                "region": source.get("region", self._region_of(url)),
                "title": entry.get("title", "无标题"),
                "summary": _clean_summary(entry.get("summary", entry.get("description", ""))),
                "source": entry.get("source", {}).get("title", feed.feed.get("title", url)),
                "author": entry.get("author", "未知"),
                "published_at": pub_str,
                "link": entry.get("link", url),
                "image": _category_icon(category),
                "tags": tags,
                "read_count": 0,
                "trending": False,
            })
        return results

    async def _fetch_all_articles(self) -> list[dict]:
        """并发抓取所有 RSS 源（单源失败跳过），返回统一格式文章列表"""
        import httpx

        articles: list[dict] = []
        # 复用同一连接池，并发拉取所有源；超时缩短到 8s 避免长尾
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            tasks = [self._fetch_one_source(client, src) for src in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                log.warning(f"RSS 并发抓取异常: {r}")
                continue
            articles.extend(r)

        # 跨源去重（基于文章链接，同一篇在多个源/RSSHub 路由出现只保留一次）。
        # 保留先出现的（sources 列表靠前的源优先级更高），其余丢弃。
        seen_links: set[str] = set()
        deduped: list[dict] = []
        dup_count = 0
        for a in articles:
            link = a.get("link") or ""
            if link in seen_links:
                dup_count += 1
                continue
            seen_links.add(link)
            deduped.append(a)
        if dup_count:
            log.info(f"RSS 跨源去重丢弃 {dup_count} 条重复文章")
        articles = deduped

        # 按发布时间排序
        articles.sort(key=lambda a: a["published_at"], reverse=True)
        # 前3篇标记为 trending
        for a in articles[:3]:
            a["trending"] = True

        return articles

    async def _get_cached_articles(self, force: bool = False, blocking: bool = True) -> list[dict]:
        """带缓存的文章获取。

        - force=True：强制刷新缓存（用于后台预热）。
        - blocking=False：非阻塞模式——仅返回已有缓存，若缓存为空则触发后台刷新
          并立即返回空列表，避免在请求链路中同步等待 20 个 RSS 源抓取（秒级延迟）。
        """
        now = datetime.now()
        if not force and self._cache and self._cache_time:
            if (now - self._cache_time).total_seconds() < self._cache_ttl:
                return self._cache
        if not blocking:
            # 非阻塞：有缓存就用，没有就后台刷新后返回空
            if self._cache is not None:
                return self._cache
            asyncio.create_task(self._fetch_all_articles_safe())
            return []
        try:
            articles = await self._fetch_all_articles()
        except Exception as e:
            # 抓取失败时不抛异常、不等待：若已有旧缓存则返回旧缓存；
            # 若连缓存都没有（首次启动且预热失败），返回 [] 让上层回退到
            # Mock 或空列表，避免用户请求被迫等满超时窗口。
            log.warning(f"RSS 抓取失败，尝试返回旧缓存: {e}")
            if self._cache is not None:
                return self._cache
            return []
        self._cache = articles
        self._cache_time = now
        return articles

    async def _fetch_all_articles_safe(self) -> None:
        """后台安全刷新缓存，异常被吞掉（不阻塞请求链路）"""
        try:
            await self._fetch_all_articles()
        except Exception as e:
            log.warning(f"后台 RSS 缓存刷新失败: {e}")

    async def warm_up(self) -> None:
        """后台预热：刷新缓存，使后续用户请求命中缓存、零等待"""
        try:
            await self._get_cached_articles(force=True)
        except Exception as e:
            log.warning(f"RSS 预热失败（不影响已有缓存）: {e}")

    async def get_categories(self) -> list[dict]:
        # 根据实际加载的 RSS 源动态生成分类标签
        cats: list[dict] = [CATEGORY_NAMES["all"]]
        seen = set()
        for src in self.sources:
            cat = src.get("category", "tech")
            if cat in seen:
                continue
            seen.add(cat)
            if cat in CATEGORY_NAMES:
                cats.append(CATEGORY_NAMES[cat])
            else:
                # 未知分类：用 id 兜底显示
                cats.append({"id": cat, "name": cat, "icon": "📰"})
        return cats

    async def get_sources(self, category: str = "all") -> dict:
        """返回某分类下实际有文章的来源，按国内/国外分组。

        结构：{"domestic": [...], "foreign": [...]}
        基于缓存文章（非阻塞），不受分页影响。
        """
        try:
            # 非阻塞：仅用已有缓存，避免触发秒级 RSS 抓取导致接口超时
            articles = await self._get_cached_articles(blocking=False)
        except Exception as e:
            log.warning(f"RSS 来源列表获取失败: {e}")
            return {"domestic": [], "foreign": []}
        if category and category != "all":
            articles = [a for a in articles if a["category"] == category]
        domestic: list[str] = []
        foreign: list[str] = []
        for a in articles:
            src = a.get("source")
            if not src:
                continue
            if a.get("region") == "foreign":
                if src not in foreign:
                    foreign.append(src)
            else:
                if src not in domestic:
                    domestic.append(src)
        return {"domestic": domestic, "foreign": foreign}

    async def get_articles(
        self, category: str = "all", keyword: str = "",
        sort: str = "latest", page: int = 1, page_size: int = 10,
        source: str = "",
    ) -> dict:
        try:
            articles = await self._get_cached_articles()
        except Exception as e:
            log.warning(f"RSS 新闻服务失败，回退到 mock: {e}")
            return await MockNewsService().get_articles(category, keyword, sort, page, page_size)
        # 缓存为空（首次启动且所有源抓取失败）时，回退到 Mock 保证有数据可看，
        # 避免首屏在预热失败情况下既不报错、又长时间空白。
        if not articles:
            return await MockNewsService().get_articles(category, keyword, sort, page, page_size)

        if category and category != "all":
            articles = [a for a in articles if a["category"] == category]
        # 按来源筛选
        if source:
            articles = [a for a in articles if a["source"] == source]
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
        if not articles:
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
