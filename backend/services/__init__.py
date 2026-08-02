"""
服务工厂 - 根据 config.yaml 配置创建对应服务实例
"""

from pathlib import Path
import yaml


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# 全局配置（延迟加载）
_config: dict | None = None


def get_config() -> dict:
    global _config
    if _config is None:
        _config = _load_config()
    return _config


def reload_config():
    """重新加载配置（用于热更新）"""
    global _config
    _config = _load_config()


def create_weather_service():
    """创建天气服务实例"""
    config = get_config()
    ds = config.get("datasource", {}).get("weather", {})
    provider = ds.get("provider", "mock")

    from .weather_service import MockWeatherService, QWeatherService

    if provider == "qweather":
        return QWeatherService(ds)
    return MockWeatherService(ds)


def create_news_service():
    """创建新闻服务实例"""
    config = get_config()
    ds = config.get("datasource", {}).get("news", {})
    provider = ds.get("provider", "mock")

    from .news_service import MockNewsService, RssNewsService

    if provider == "rss":
        return RssNewsService(ds)
    return MockNewsService(ds)


def create_price_service():
    """创建比价服务实例"""
    config = get_config()
    ds = config.get("datasource", {}).get("price", {})
    provider = ds.get("provider", "mock")

    from .price_service import MockPriceService

    # 未来可扩展: if provider == "crawler" -> return CrawlerPriceService(ds)
    return MockPriceService(ds)


def create_nearby_service():
    """创建周边资源服务实例（委托给可插拔的 POI 数据源）"""
    config = get_config()
    from .nearby_service import NearbyService
    return NearbyService(config)


# 实时定位服务（天气/周边共享的当前位置，由前端设备定位上报覆盖）
from . import geolocation  # noqa: E402
