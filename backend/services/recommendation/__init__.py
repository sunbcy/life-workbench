"""
推荐引擎 — 综合入口

Usage:
    from services.recommendation import RecommendationEngine
    engine = RecommendationEngine(profile_dir="~/.life-workbench/profile")
    scored_items = engine.rank(items, item_type="news")
"""

from .profile_loader import ProfileLoader
from .vectorizer import UserVectorizer, ItemVectorizer
from .scorer import Scorer
from .ranker import Ranker


class RecommendationEngine:
    """个性化推荐引擎"""

    def __init__(self, profile_dir: str = "~/.life-workbench/profile"):
        self.profile_loader = ProfileLoader(profile_dir)
        self.user_vectorizer = UserVectorizer()
        self.item_vectorizer = ItemVectorizer()
        self.scorer = Scorer()
        self.ranker = Ranker()

    def initialize(self):
        """加载用户画像"""
        self.profile_loader.load_all()

    def reload_profile(self):
        """重新加载用户画像（配置文件更新后调用）"""
        self.profile_loader.load_all()

    @property
    def profile(self) -> dict:
        """获取完整用户画像"""
        return self.profile_loader.profile

    @property
    def profile_summary(self) -> dict:
        """获取脱敏的画像摘要"""
        return self.profile_loader.summary()

    @property
    def dimensions(self) -> list[dict]:
        """获取各维度状态"""
        return self.profile_loader.dimensions_status()

    def recommend(
        self, items: list[dict], item_type: str = "news",
        preserve_order: bool = False,
        mode: str = "rank",
        pin_limit: int | None = None,
        pin_threshold: float | None = None,
    ) -> list[dict]:
        """
        对一批内容项进行个性化评分和排序

        Args:
            items: 原始内容项列表
            item_type: news | product | nearby
            preserve_order: 兼容旧调用。True 等价于 mode="score_only"。
            mode: 排列策略
                - "rank"        : 按综合分重排 + 多样性（推荐流）
                - "priority"    : Feedly 优先收件箱 —— 时间线不变，高分置顶
                - "score_only"  : 只打分，完全不改变顺序
            pin_limit / pin_threshold: 仅 mode="priority" 时生效

        Returns:
            带 _recommendation 字段的列表
        """
        if not items:
            return items

        if preserve_order:
            mode = "score_only"

        user_vector = self.user_vectorizer.vectorize(self.profile_loader.profile)

        for item in items:
            item_vector = self.item_vectorizer.vectorize(item, item_type)
            item["_recommendation"] = self.scorer.score(
                user_vector, item_vector, item, item_type
            )

        if mode == "score_only":
            return items
        if mode == "priority":
            return self.ranker.priority_inbox(
                items, pin_threshold=pin_threshold, pin_limit=pin_limit
            )
        return self.ranker.rank(items, item_type)

    def score_mixed(self, items: list[dict]) -> list[dict]:
        """
        对带 _type 字段的混合内容列表一次性评分。

        与逐条调用 recommend 相比，只计算一次用户向量，
        避免对每条内容重复 vectorize 整份画像（feed 接口有 30+ 条内容，
        逐条调用会把用户向量重算 30+ 次）。

        注意：会就地弹出每项中的 _type 字段，保持响应结构与 recommend 一致。
        """
        if not items:
            return items

        user_vector = self.user_vectorizer.vectorize(self.profile_loader.profile)

        for item in items:
            item_type = item.pop("_type", "news")
            item_vector = self.item_vectorizer.vectorize(item, item_type)
            item["_recommendation"] = self.scorer.score(
                user_vector, item_vector, item, item_type
            )

        return items


# 全局单例
_engine: RecommendationEngine | None = None


def get_engine(profile_dir: str | None = None) -> RecommendationEngine:
    """获取推荐引擎单例"""
    global _engine
    if _engine is None:
        import os
        if profile_dir is None:
            profile_dir = os.path.expanduser("~/.life-workbench/profile")
        _engine = RecommendationEngine(profile_dir)
        _engine.initialize()
    return _engine


def reload_engine(profile_dir: str | None = None):
    """重新加载推荐引擎"""
    global _engine
    import os
    if profile_dir is None:
        profile_dir = os.path.expanduser("~/.life-workbench/profile")
    if _engine is None:
        _engine = RecommendationEngine(profile_dir)
    _engine.reload_profile()
