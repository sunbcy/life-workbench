"""
排序器 — 综合排序、去重、多样性保证

提供两种排列策略:
  1. rank()      : 纯分数降序 + 多样性重排（推荐流场景）
  2. priority_inbox() : Feedly「优先收件箱」模式 —— 时间线顺序不变，
                        只把高分内容抽出置顶（个人资讯工具更自然的交互）
"""


class Ranker:
    """排序与多样性控制"""

    # 进入置顶区的最低分数门槛
    DEFAULT_PIN_THRESHOLD = 0.5
    # 置顶区最大容量（过多会退化成「全部重排」，失去时间线意义）
    DEFAULT_PIN_LIMIT = 3

    def __init__(self, diversity_factor: float = 0.15):
        """
        Args:
            diversity_factor: 多样性权重（越高越不容易出现同类扎堆）
        """
        self.diversity_factor = diversity_factor

    def rank(self, items: list[dict], item_type: str = "news") -> list[dict]:
        """
        对带 _recommendation 的 items 进行排序
        1. 按 composite_score 降序
        2. 应用多样性惩罚（同类内容扎堆时降低后续项的分数）
        """
        if not items:
            return items

        # 按综合分数排序
        items.sort(
            key=lambda x: x.get("_recommendation", {}).get("composite_score", 0),
            reverse=True,
        )

        # 多样性重排：前 N 项确保类别多样性
        items = self._diversify_top(items, top_n=5)

        return items

    def priority_inbox(
        self,
        items: list[dict],
        pin_threshold: float | None = None,
        pin_limit: int | None = None,
        require_personalized: bool = True,
    ) -> list[dict]:
        """Feedly「优先收件箱」模式：时间线 + 高分置顶区。

        与 rank() 的区别：**不打乱整体时间线**，只把少数高分内容提到最前面，
        并给它们打上 `_pinned` 标记供前端渲染「为你精选」分区。
        这样既保留了「按时间浏览」的心智模型，又让个性化真正影响可见性
        —— 此前 preserve_order=True 导致 Ranker 完全是死代码。

        Args:
            items: 已按时间线排好序的内容项（须已带 _recommendation）
            pin_threshold: 置顶分数门槛
            pin_limit: 置顶区最大条数
            require_personalized: 仅允许「个性化命中」的内容进入置顶区，
                避免纯靠新鲜度刷高分的内容霸占置顶位

        Returns:
            [置顶项...] + [其余项保持原时间线顺序]
        """
        if not items:
            return items

        threshold = self.DEFAULT_PIN_THRESHOLD if pin_threshold is None else pin_threshold
        limit = self.DEFAULT_PIN_LIMIT if pin_limit is None else pin_limit

        if limit <= 0:
            for it in items:
                it["_pinned"] = False
            return items

        candidates = []
        for idx, item in enumerate(items):
            rec = item.get("_recommendation") or {}
            score = rec.get("composite_score", 0)
            if score < threshold:
                continue
            # 只有真正命中画像的内容才配置顶，否则「置顶区」会变成
            # 「最新 3 条」的另一种写法（这正是原 trending 标记的问题）。
            if require_personalized and not rec.get("personalized"):
                continue
            candidates.append((idx, item))

        if not candidates:
            for it in items:
                it["_pinned"] = False
            return items

        # 高分优先；同分时保持时间线先后（idx 小者靠前）
        candidates.sort(
            key=lambda p: (
                -(p[1].get("_recommendation", {}).get("composite_score", 0)),
                p[0],
            )
        )

        # 置顶区内部做类别去重，避免 3 条置顶全是同一个分类
        pinned: list[dict] = []
        pinned_idx: set[int] = set()
        seen_categories: set[str] = set()
        for idx, item in candidates:
            if len(pinned) >= limit:
                break
            category = item.get("category", "unknown")
            if category in seen_categories:
                continue
            seen_categories.add(category)
            pinned.append(item)
            pinned_idx.add(idx)

        # 注意：此处刻意不做「补齐空位」。
        # 置顶区的价值在于「少而不同」——若为了凑满 limit 而放进同类文章，
        # 就退化成了单一类目霸屏，与多样性目标相悖。宁可只置顶 1~2 条。

        rest = [item for idx, item in enumerate(items) if idx not in pinned_idx]

        for it in pinned:
            it["_pinned"] = True
        for it in rest:
            it["_pinned"] = False

        return pinned + rest

    def _diversify_top(self, items: list[dict], top_n: int = 5) -> list[dict]:
        """确保前 top_n 个结果来自多样化的维度"""
        if len(items) <= top_n:
            return items

        seen_categories = set()
        result = []
        rest = []

        for item in items:
            rec = item.get("_recommendation", {})
            category = item.get("category", "unknown")

            # 类别不同或维度不同 → 优先保留
            if len(result) < top_n:
                if category not in seen_categories:
                    seen_categories.add(category)
                    result.append(item)
                else:
                    # 同类内容，轻微降低分数
                    rec["composite_score"] = round(rec.get("composite_score", 0) * (1 - self.diversity_factor), 3)
                    rest.append(item)
            else:
                rest.append(item)

        # 剩余项按调整后的分数重新排序
        rest.sort(
            key=lambda x: x.get("_recommendation", {}).get("composite_score", 0),
            reverse=True,
        )

        return result + rest

    def top_k(self, items: list[dict], k: int = 10, min_score: float = 0.2) -> list[dict]:
        """返回 top-K，过滤低于阈值的项"""
        ranked = self.rank(items)
        return [
            item for item in ranked[:k]
            if item.get("_recommendation", {}).get("composite_score", 0) >= min_score
        ]
