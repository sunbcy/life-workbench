"""
POI 数据源工厂

根据 config.yaml 的 datasource.nearby.provider 选择具体实现：
  mock  -> MockPOIProvider（内置数据，兜底）
  amap  -> AmapPOIProvider（高德地图）
  baidu -> BaiduPOIProvider（百度地图）

未配置 API Key 或请求失败时，由 NearbyService 自动回退到 Mock。
"""
from .base import BasePOIProvider
from .mock_provider import MockPOIProvider


def create_poi_provider(config: dict, force_mock: bool = False) -> BasePOIProvider:
    ds = config.get("datasource", {}).get("nearby", {})
    provider = ds.get("provider", "mock")
    if force_mock:
        provider = "mock"

    if provider == "amap":
        from .amap_provider import AmapPOIProvider
        return AmapPOIProvider(config)
    if provider == "baidu":
        from .baidu_provider import BaiduPOIProvider
        return BaiduPOIProvider(config)
    return MockPOIProvider(config)


__all__ = ["BasePOIProvider", "MockPOIProvider", "create_poi_provider"]
