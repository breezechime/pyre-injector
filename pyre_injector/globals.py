"""
Global registry for the active dependency container.
活动依赖容器的全局注册表。
"""
from typing import Optional

from .container import DependencyContainer


class DependencyContainerProxy:
    """Holds the process-wide active :class:`DependencyContainer`.
    持有进程内当前活动的依赖容器实例。
    """

    def __init__(self) -> None:
        self.instance: Optional[DependencyContainer] = None

    def set_instance(self, instance: Optional[DependencyContainer]) -> None:
        """Set the active container instance. 设置活动容器实例。"""
        self.instance = instance

    def __get__(self, instance, owner):
        return self.instance


# Global active container instance / 全局活动容器实例
_active = DependencyContainerProxy()
