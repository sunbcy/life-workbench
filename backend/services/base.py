"""
服务抽象基类 - 定义各数据服务的统一接口
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseService(ABC):
    """所有数据服务的抽象基类"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @property
    def name(self) -> str:
        return self.__class__.__name__
