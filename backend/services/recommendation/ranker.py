"""
排序器 — 综合排序、去重、多样性保证
"""

import math


class Ranker:
    """排序与多样性控制"""

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
        3. 确保前3个来自不同 match_dimensions
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

    def _diversify_top(self, items: list[dict], top_n: int = 5) -> list[dict]:
        """确保前 top_n 个结果来自多样化的维度"""
        if len(items) <= top_n:
            return items

        seen_categories = set()
        result = []
        rest = []

        for item in items:
            rec = item.get("_recommendation", {})
            dims = tuple(rec.get("match_dimensions", ["unknown"]))
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
