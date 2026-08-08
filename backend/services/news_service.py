"""
新闻服务 - Mock 实现 + RSS 真实数据源实现
"""

import logging
import hashlib
import asyncio
import re
from datetime import datetime, timezone, timedelta

from services import geolocation

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

    def _name_of(self, url: str) -> str:
        """根据 URL 推断可读的源名字，供日志/来源列表展示。

        - rsshub://huxiu/article 或 https://rsshub.xxx/huxiu/article -> huxiu
        - https://www.36kr.com/feed -> 36kr
        - https://sspai.com/feed   -> sspai
        """
        if not url:
            return "未知源"
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            # RSSHub 路由：用路径第一段作为名字（huxiu/article -> huxiu）
            if "rsshub" in host:
                path_seg = [p for p in parsed.path.split("/") if p]
                if path_seg:
                    return path_seg[0]
            # 去掉 www. 前缀
            if host.startswith("www."):
                host = host[4:]
            # 取主域名第一段
            name = host.split(".")[0] if host else host
            return name or host or url
        except Exception:
            return url

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
            # 预计算每个源的可读名字，供日志/来源列表展示（rsshub 用路由名，
            # 普通 URL 用域名），便于调试时一眼看出访问的是哪个源
            src.setdefault("name", self._name_of(src.get("url", "")))
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
        name = source.get("name", url)
        category = source.get("category", "tech")
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        }
        log.info("RSS 抓取开始: name=%s url=%s", name, url)
        try:
            resp = await client.get(url, headers=headers, timeout=self._SOURCE_TIMEOUT)
            resp.raise_for_status()
            # 解析本身不联网，但用 wait_for 防止超大/畸形响应体长时间占 CPU
            feed = await asyncio.wait_for(
                asyncio.to_thread(feedparser.parse, resp.text),
                timeout=self._PARSE_TIMEOUT,
            )
        except Exception as e:
            log.warning("RSS 源抓取失败: name=%s url=%s err=%s", name, url, e)
            return []

        # 抓取成功，打印名字 + 链接 + 实际返回条数，便于调试
        feed_title = feed.feed.get("title", url)
        log.info(
            "RSS 抓取成功: name=%s title=%s url=%s 文章数=%d",
            name, feed_title, url, len(feed.entries),
        )

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

        # 内容级跨平台去重：不仅按完全相同的链接，还按标题语义相似度
        # 过滤不同平台报道的「同一事件」（相同内容性质的新闻）。
        # 保留先出现的（sources 列表靠前的源优先级更高），其余丢弃。
        deduped, dup_count, link_dup = dedup_by_content(articles)
        if link_dup:
            log.info(f"RSS 链接去重丢弃 {link_dup} 条完全相同链接的文章")
        if dup_count:
            log.info(f"RSS 内容去重丢弃 {dup_count} 条跨平台相似文章")
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

        # 始终注入「当地新闻」标签：基于当前地理位置（城市）动态命名，
        # 让资讯中心根据用户的实时位置呈现本地化入口。若存在同名兜底
        # 分类（local）则就地改写名字，否则在「推荐」之后插入。
        city = geolocation.get_location().get("city") or "本地"
        local_cat = {"id": "local", "name": f"{city}·本地", "icon": "📍"}
        replaced = False
        for i, c in enumerate(cats):
            if c["id"] == "local":
                cats[i] = local_cat
                replaced = True
                break
        if not replaced:
            # 插在「推荐」之后、其余分类之前，保证本地入口醒目
            cats.insert(1, local_cat)
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
            # 当地新闻：不仅包含标记为 local 的源，还纳入所有
            # 标题/摘要提到当前城市的内容（尽量全），来源名也随之聚合
            if category == "local":
                city = geolocation.get_location().get("city", "")
                district = geolocation.get_location().get("district", "")
                articles = [a for a in articles if _is_local(a, city, district)]
            else:
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

    # ============================================================
    # 待接入渠道清单（前端展示「更多来源」入口，标注 pending）
    # ------------------------------------------------------------
    # 业界做本地资讯聚合的常见补充手段，目前均未在 config.yaml 启用，
    # 仅在前端保留入口并标注「待接入」，便于后续按需接入：
    #   - weixin   : 微信公众号（本地媒体/街道/政务号独家，需微信 Cookie，反爬严）
    #   - toutiao  : 今日头条地域内容流（cu 参数按城市，内容杂需清洗）
    #   - weibo    : 微博「深圳同城」话题（营销多需清洗）
    #   - douyin   : 抖音同城/地缘视频流（结构化差）
    #   - crawl    : 直接爬列表页（最灵活最脆，需看 robots/版权）
    #   - paid_api : 商业舆情 API（天眼查/百度舆情/清博/新榜，付费最稳，企业级）
    # ============================================================
    _PENDING_CHANNELS = [
        {
            "id": "weixin", "name": "微信公众号", "icon": "💬",
            "status": "pending",
            "note": "本地媒体/街道/政务号独家内容；需有效微信 Cookie，反爬严、易封，维护成本高。",
            "category": "local",
            "example": "rsshub://weixin/sznews_com（自建 RSSHub 后启用）",
        },
        {
            "id": "toutiao", "name": "今日头条", "icon": "📰",
            "status": "pending",
            "note": "按城市内容流（cu 参数）；内容杂、营销多，需较强清洗。",
            "category": "local",
            "example": "rsshub://toutiao/category/新闻/city/深圳",
        },
        {
            "id": "weibo", "name": "微博同城", "icon": "🐦",
            "status": "pending",
            "note": "「深圳同城」话题流；营销/水军多，需清洗。",
            "category": "local",
            "example": "rsshub://weibo/keyword/深圳同城",
        },
        {
            "id": "douyin", "name": "抖音同城", "icon": "🎬",
            "status": "pending",
            "note": "同城/地缘短视频流；结构化差，需转写为可读资讯。",
            "category": "local",
            "example": "rsshub://douyin/keyword/深圳",
        },
        {
            "id": "crawl", "name": "官网直爬", "icon": "🕷️",
            "status": "pending",
            "note": "直接抓深圳新闻网等列表页 DOM；最灵活但最脆，前端改版即挂，需看 robots/版权。",
            "category": "local",
            "example": "routes/shenzhen/news.js（自建 RSSHub 自定义路由）",
        },
        {
            "id": "paid_api", "name": "商业舆情 API", "icon": "💎",
            "status": "pending",
            "note": "天眼查/百度舆情/清博/新榜等按城市推送本地舆情；付费最稳，适合企业级。",
            "category": "local",
            "example": "需商务对接 API Key",
        },
    ]

    def get_channels(self) -> list[dict]:
        """返回待接入渠道清单（前端「更多来源」入口，标注 pending）。

        与 get_sources 不同：这里不依赖缓存文章，返回的是「渠道能力清单」，
        用于在前端保留各补充渠道的入口并标注待接入，便于后续按需启用。
        """
        return list(self._PENDING_CHANNELS)

    async def get_articles(
        self, category: str = "all", keyword: str = "",
        sort: str = "latest", page: int = 1, page_size: int = 10,
        source: str = "", geo_scope: str = "",
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
            # 当地新闻：把各平台里提及当前城市/区的内容都聚合进来（尽量全），
            # 不限于源分类为 local 的文章。
            if category == "local":
                city = geolocation.get_location().get("city", "")
                district = geolocation.get_location().get("district", "")
                articles = [a for a in articles if _is_local(a, city, district)]
                # 真实 RSS 中本地内容可能很少甚至为空（源本身偏全国/国际），
                # 此时回退到 Mock 的本地文章兜底，保证「当地新闻」始终有相关内容可看。
                if not articles:
                    mock_local = await MockNewsService().get_articles(category="local")
                    articles = mock_local.get("articles", [])
                # 对 local 类源做关键词聚焦降噪：检索型本地源（如 Google News
                # 按「深圳」检索）可能返回仅「相关」但不含城市名的条目，需剔除。
                # Mock 兜底文章标题本就含深圳/区名，不受影响。
                articles = [a for a in articles if _local_source_focus(a, city, district)]
                # 当地新闻 + 地理圈层：按维度一/二做范围过滤与影响范围优先排序
                articles = filter_and_rank_by_geo(articles, geo_scope or "district", city, district)
            else:
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

        # 地理圈层（geo_scope）独立于分类时也生效：对结果按影响范围优先置顶。
        # 注意：当 category==local 时已内部处理，这里覆盖其余场景。
        if geo_scope and category != "local":
            city = geolocation.get_location().get("city", "")
            district = geolocation.get_location().get("district", "")
            articles = filter_and_rank_by_geo(articles, geo_scope, city, district)

        # 排序：geo_scope 激活时以「影响范围」为优先维度（维度一要求），
        # 其余情况沿用用户选择的 sort。
        if geo_scope:
            # 已按 _geo.score 降序；同分时新近优先
            articles.sort(
                key=lambda a: (a.get("_geo", {}).get("score", 0), a.get("published_at", "")),
                reverse=True,
            )
        elif sort == "latest":
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


# ============================================================
# 地理位置影响范围评分（维度一 & 维度二）
# ----------------------------------------------------------------
# 设计目标（来自需求）：
#   维度一：区级别新闻优先，且「影响范围 / 影响概率」越大越靠前 ——
#           即新闻涉及的地理粒度越精确到用户所在区、对用户的实质影响越大，
#           排序越优先。
#   维度二：地理圈层可放大 —— 从「区」(district) 扩大到「市」(city)，
#           由 geo_scope 参数控制。
#
# 实现：
#   1) 解析每条新闻涉及的「最高地理粒度」(区/市/省/全国/无)；
#   2) 计算「影响范围评分」：粒度越精确、与用户区越贴合分越高；
#   3) geo_scope 控制圈层：district 仅保留含区/市名（且非泛全国）的，
#      city 扩大到全市（含市名即可，含区名更高优先）。
# ============================================================

# 深圳行政区（用于「区级别」精确命中）。新增城市只需在此补充对应区列表。
_DISTRICTS_BY_CITY: dict[str, list[str]] = {
    "深圳": ["福田", "罗湖", "南山", "宝安", "龙岗", "龙华", "坪山", "光明", "盐田", "大鹏"],
    "北京": ["东城", "西城", "朝阳", "海淀", "丰台", "石景山", "通州", "顺义", "昌平", "大兴", "怀柔", "平谷", "门头沟", "房山", "密云", "延庆"],
    "上海": ["黄浦", "徐汇", "长宁", "静安", "普陀", "虹口", "杨浦", "闵行", "宝山", "嘉定", "浦东", "松江", "青浦", "奉贤", "金山", "崇明"],
    "广州": ["越秀", "海珠", "荔湾", "天河", "白云", "黄埔", "番禺", "花都", "南沙", "从化", "增城"],
}

# 省级关键词（用于识别「省级」粒度）
_PROVINCE_KEYWORDS = ["省", "广东", "江苏", "浙江", "北京", "上海", "天津", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
                     "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南", "海南", "四川", "贵州", "云南", "陕西", "甘肃",
                     "青海", "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门"]

# 全国/泛化标记：命中说明影响范围是全国性，与本地弱相关
_NATION_KEYWORDS = ["全国", "全国两会", "我国", "国家", "国务院", "央行", "工信部", "发改委", "全球", "世界", "国际", "海外"]

# 粒度等级权重：越接近用户所在区，基础分越高（影响范围越聚焦、影响概率越大）
_GEO_TIER_WEIGHT = {
    "district": 1.0,   # 精确到区：直接影响用户生活圈
    "city": 0.7,       # 全市：较大影响范围
    "province": 0.4,   # 省级：间接影响
    "nation": 0.15,    # 全国：弱相关
    "none": 0.0,       # 无地理属性
}


def _geo_grain_of(article: dict, city: str, district: str) -> tuple[str, str]:
    """解析新闻涉及的最高地理粒度。

    返回 (grain, hit_name)：
      grain ∈ {district, city, province, nation, none}
      hit_name 为命中的行政区/城市名（用于展示「影响范围」）。
    优先级：区 > 市 > 省 > 全国。标题优先于摘要（避免摘要噪声）。
    """
    title = article.get("title", "") or ""
    summary = article.get("summary", "") or ""
    text_title = title
    text_full = f"{title} {summary}"

    # 1) 区级别（最精确）
    districts = _DISTRICTS_BY_CITY.get(city, [])
    for d in districts:
        if d in text_title:
            return "district", d
    # 用户所在区名单独校验（即使不在预设列表，也能识别「南山区」这类）
    if district and len(district) >= 2 and district in text_title:
        return "district", district

    # 2) 全国/泛化（弱本地）
    if any(w in text_title for w in _NATION_KEYWORDS):
        return "nation", "全国"

    # 3) 市级
    if city and city in text_title:
        return "city", city

    # 4) 省级（在全文里找）
    for p in _PROVINCE_KEYWORDS:
        if p in text_title:
            return "province", p

    # 回退到全文再判一次（摘要可能含更精确粒度）
    for d in districts:
        if d in text_full:
            return "district", d
    if district and len(district) >= 2 and district in text_full:
        return "district", district
    if any(w in text_full for w in _NATION_KEYWORDS):
        return "nation", "全国"
    if city and city in text_full:
        return "city", city
    for p in _PROVINCE_KEYWORDS:
        if p in text_full:
            return "province", p

    return "none", ""


def _geo_impact_score(article: dict, city: str, district: str) -> dict:
    """计算新闻对用户的「地理影响范围评分」。

    分数 = 粒度基础分 × 与用户区的贴合度调节，并产出可解释标签。
    返回 {score, grain, scope_label}，score ∈ [0, 1.2]。
    """
    grain, hit = _geo_grain_of(article, city, district)
    base = _GEO_TIER_WEIGHT.get(grain, 0.0)

    # 贴合度调节：若新闻精确到用户「所在区」，再额外加权（影响概率最大）
    boost = 0.0
    if grain == "district" and district and hit == district:
        boost = 0.2          # 正好命中用户所在区
    elif grain == "city" and city and hit == city:
        boost = 0.0          # 全市正常分
    elif grain == "district" and district and hit != district:
        boost = 0.05         # 同市其他区，仍属强本地但略低于本区

    score = min(1.2, base + boost)

    # 人类可读的影响范围标签
    scope_label = {
        "district": f"影响范围：{hit}（区）",
        "city": f"影响范围：{hit}（全市）",
        "province": f"影响范围：{hit}（省）",
        "nation": "影响范围：全国",
        "none": "",
    }.get(grain, "")

    return {"score": round(score, 3), "grain": grain, "scope_label": scope_label, "hit": hit}


def filter_and_rank_by_geo(
    articles: list[dict],
    geo_scope: str,
    city: str,
    district: str,
) -> list[dict]:
    """按地理圈层过滤 + 按影响范围优先排序（维度一 & 维度二）。

    geo_scope:
      "district" : 只保留区/市级（剔除纯全国/无地理属性），区 > 市 优先；
      "city"     : 扩大到全市，含市名即可（区 > 市 仍优先），保留省/全国作为兜底补充；
      其他/空    : 不过滤，仅做影响范围评分便于前端展示。
    不修改原顺序的其余维度，仅对「地理相关」内容做优先置顶。
    """
    scored: list[dict] = []
    for a in articles:
        g = _geo_impact_score(a, city, district)
        a = dict(a)  # 浅拷贝，避免污染缓存原始数据
        a["_geo"] = g
        scored.append(a)

    if geo_scope == "district":
        # 圈层最小：只收区/市粒度，按影响分降序
        kept = [a for a in scored if a["_geo"]["grain"] in ("district", "city")]
        kept.sort(key=lambda a: a["_geo"]["score"], reverse=True)
        return kept
    if geo_scope == "city":
        # 圈层放大到全市：区/市优先置顶，省/全国作为后续补充（仍按影响分）
        kept = [a for a in scored if a["_geo"]["grain"] in ("district", "city", "province", "nation")]
        kept.sort(key=lambda a: a["_geo"]["score"], reverse=True)
        return kept

    # 不过滤：全部保留，仅按影响分排序（便于「推荐」流里地理信号参与加权）
    scored.sort(key=lambda a: a["_geo"]["score"], reverse=True)
    return scored


# ============================================================
# 当地新闻判定
# ============================================================

def _local_source_focus(article: dict, city: str, district: str = "") -> bool:
    """对「源分类本就是 local」的文章做关键词聚焦降噪。

    背景：local 类源（如 Google News 按「深圳」检索的 feed）返回的结果可能只是
    「相关」而非标题/摘要真正含城市名。_is_local 对 category==local 直接放行，
    会把这些噪声整批带进来。此函数要求：源分类为 local 时，标题/摘要必须真的
    包含 city 或 district，否则视为噪声剔除。

    非 local 类源（靠 _is_local 文本判定进来的）不受此约束，保持原聚合逻辑。
    """
    if article.get("category") != "local":
        return True
    if not city and not district:
        # 定位缺失时不强滤，避免把本地源内容全清掉
        return True
    title = article.get("title", "")
    summary = article.get("summary", "")
    text = f"{title} {summary}"
    if city and city in text:
        return True
    if district and len(district) >= 2 and district in text:
        return True
    return False


def _is_local(article: dict, city: str, district: str = "") -> bool:
    """判断一条新闻是否属于「当地新闻」。

    规则（尽量全，覆盖跨平台报道）：
      1) 源分类本就是 local；
      2) 或标题/摘要文本中包含当前城市名 / 区名。
    仅当城市名为空（定位缺失）时退化为只看 local 分类，
    避免空关键词把全部新闻误判为当地。

    判定可靠性（避免「标题顺带提到城市名」的泛新闻被误判为当地）：
      1) 源分类本就是 local —— 强信号，直接命中；
      2) 城市名作为本地事件主语：出现在标题、且（标题以城市名开头，或标题/摘要
         含本地民生语义词，如 地铁/发布/消费券/天气/预警/景区…）；
      3) 区名（如「南山」）出现在标题 —— 更精确，直接命中；
      4) 排除词（多地/全国/全球…）出现时视为非本地专属报道，不命中，
         避免「北京上海深圳等多地…」被算作深圳本地。
    """
    if article.get("category") == "local":
        return True
    if not city:
        return False
    title = article.get("title", "")
    summary = article.get("summary", "")
    text = f"{title} {summary}"

    # 排除明显非本地专属的「多地/全国」类报道
    if any(w in title for w in _NON_LOCAL_MARKERS):
        return False

    # 区名出现在标题：精确到区，直接算当地
    if district and len(district) >= 2 and district in title:
        return True

    # 城市名需作为本地事件主语：标题含城市名，且标题含本地民生/市政语义词。
    # 本地词只在标题中匹配，避免摘要里的泛提及造成误判；不使用「以城市名开头」
    # 直接命中，以免「深圳XX产业/公司发布会」这类泛新闻被误判为当地。
    if city and city in title and any(w in title for w in _LOCAL_WORDS):
        return True
    return False


# 本地民生/市政/地理语义词：标题含其一且与城市名共现时，认定为该地新闻。
# 仅保留强本地信号（交通/天气/市政/民生/文教/地理/疫情），剔除「产业/人才/
# 补贴/房价」等易致泛经济新闻误判的宽泛词。
_LOCAL_WORDS = {
    "区", "县", "街道", "镇", "社区", "地铁", "公交", "轻轨", "出租车", "高铁", "火车站",
    "发布", "通知", "公示", "通报", "公告", "声明", "批复", "规划", "建设", "开工", "竣工",
    "封顶", "开通", "启用", "投用", "通车", "通航", "整治", "改造", "拆迁", "征收", "腾退",
    "便民", "民生", "就医", "入学", "招生", "升学", "学区", "交通", "限行", "停车", "堵车",
    "天气", "预警", "暴雨", "台风", "高温", "寒潮", "大风", "冰雹", "停水", "停电", "断水",
    "活动", "演出", "展览", "赛事", "文旅", "消费券", "落户", "社保", "医保",
    "公园", "景区", "绿道", "学校", "医院", "卫生院", "市场", "超市", "商场", "菜场",
    "图书馆", "体育馆", "文化馆", "路口", "大道", "高架", "桥梁", "隧道", "口岸", "机场",
    "港口", "码头", "排水", "内涝", "核酸", "疫苗", "防疫", "创文", "文明", "宜居",
    "确诊", "病例", "疫情", "本土", "无症状", "隔离", "封控", "防控", "轨迹", "发热",
    "就诊", "保供", "物资", "菜篮子", "米袋子",
}

# 非本地专属标记：标题含这些词时，即便提到城市名也不算该地新闻
_NON_LOCAL_MARKERS = {
    "多地", "全国", "全球", "各省", "各省市", "各省份", "多城", "31省", "31个省份",
    "多省市", "各地", "一线城市",
}


# ============================================================
# 内容级跨平台去重（相同内容性质的新闻）
# ============================================================

# 标题相似度阈值：超过即视为「同一事件的不同平台报道」，仅保留一条
_CONTENT_DUP_THRESHOLD = 0.80


def _norm_title(title: str) -> str:
    """标题归一化：去空白/标点/控制符，转小写，便于相似度比较。

    保留中文与字母数字，去掉「！？。，、」等干扰字符，
    使「深圳发布暴雨预警！」与「深圳发布暴雨预警」可判定为同一事件。
    """
    if not title:
        return ""
    s = title.lower()
    # 去除常见中英文标点与空白
    s = re.sub(r"[\s\u3000]+", "", s)
    s = re.sub(r"[!！?？。.，,、；;:：\"'“”‘’()（）\[\]【】<>《》|｜/\\~`@#$%^&*\-_=+…·.．]", "", s)
    return s


def _bigrams(s: str) -> set[str]:
    """生成字符级 2-gram 集合（中文标题相似度的稳定特征）"""
    if len(s) <= 1:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _title_sim(a: str, b: str) -> float:
    """两标题的语义相似度（基于 2-gram 的 Jaccard 相似系数）。

    返回 0~1，1 表示完全相同。对中文标题的同义改写、标点差异稳健。
    """
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return 0.0
    # 完全相同（归一化后）直接命中
    if na == nb:
        return 1.0
    ga, gb = _bigrams(na), _bigrams(nb)
    if not ga or not gb:
        return 0.0
    inter = ga & gb
    union = ga | gb
    if not union:
        return 0.0
    # Jaccard 基础上叠加双向包含度，缓解长短标题不对称
    jaccard = len(inter) / len(union)
    contain = max(len(inter) / len(ga), len(inter) / len(gb))
    return 0.5 * jaccard + 0.5 * contain


def dedup_by_content(articles: list[dict]) -> tuple[list[dict], int, int]:
    """内容级跨平台去重。

    两道关卡：
      1) 链接完全相同（同一篇在多个 RSSHub 路由/源出现）—— 硬去重；
      2) 标题相似度 >= 阈值（不同平台报道同一事件）—— 软去重。
    保留先出现的（sources 列表靠前 = 优先级更高），其余丢弃。
    返回 (去重后列表, 内容相似丢弃数, 链接相同丢弃数)。
    """
    seen_links: set[str] = set()
    kept_titles: list[str] = []  # 已保留文章的标题，用于相似度比对
    out: list[dict] = []
    content_dup = 0
    link_dup = 0
    for a in articles:
        link = a.get("link") or ""
        if link:
            if link in seen_links:
                link_dup += 1
                continue
            seen_links.add(link)
        # 内容相似度比对：与任一已保留文章足够相似则视为重复
        title = a.get("title", "")
        is_dup = False
        for kt in kept_titles:
            if _title_sim(title, kt) >= _CONTENT_DUP_THRESHOLD:
                is_dup = True
                break
        if is_dup:
            content_dup += 1
            continue
        kept_titles.append(title)
        out.append(a)
    return out, content_dup, link_dup
