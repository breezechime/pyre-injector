"""
Pyre Injector - a small dependency injection framework.
Pyre Injector - 轻量级依赖注入框架。

Register dependencies with ``@inject`` / ``container.inject(...)`` and read them
back with ``container.provider(...)`` / ``autowired(...)``.
用 ``@inject`` / ``container.inject(...)`` 注册依赖，
用 ``container.provider(...)`` / ``autowired(...)`` 获取依赖。
"""
from typing import Optional, Type

from .constants import _T
from .container import (
    DependencyAlreadyRegisteredError,
    DependencyAnnotationError,
    DependencyContainer,
    DependencyCycleError,
    DependencyDefinition,
    DependencyError,
    DependencyInitError,
    DependencyNotInitializedError,
    DependencyNotRegisteredError,
    describe_exception,
    describe_target,
)
from .globals import _active

__all__ = [
    'inject',
    'autowired',
    'provider',
    'DependencyContainer',
    'DependencyDefinition',
    'DependencyError',
    'DependencyNotRegisteredError',
    'DependencyAlreadyRegisteredError',
    'DependencyNotInitializedError',
    'DependencyInitError',
    'DependencyAnnotationError',
    'DependencyCycleError',
    'describe_target',
    'describe_exception',
]


def inject(
    clazz: Optional[Type[_T]] = None,
    depend_name: Optional[str] = None,
    scope: Optional[str] = None,
    lazy_init: Optional[bool] = None,
    return_type: Optional[Type[type]] = None,
    solve_init: bool = True,
    replace: bool = False,
):
    """Register a class or factory function as a dependency.
    将类或工厂函数注册为依赖。

    Usage:
        @inject
        class MyService:
            ...

        @inject(scope='prototype', lazy_init=True)
        class MyService:
            ...
    """
    return DependencyContainer.inject(
        clazz,
        depend_name=depend_name,
        scope=scope,
        lazy_init=lazy_init,
        return_type=return_type,
        solve_init=solve_init,
        replace=replace,
    )


def autowired(clazz: Type[_T]) -> _T:
    """Return the instance registered for ``clazz`` from the active container.
    从活动容器中按类型获取依赖实例。
    """
    instance = _active.instance
    if not instance:
        raise DependencyNotInitializedError(
            "DependencyContainer is not initialized. "
            "依赖容器未初始化。"
            " Please call container.init_dependency_container() first."
            " 请先调用 container.init_dependency_container()。"
        )
    return instance.provider(clazz)


def provider(clazz: Type[_T]) -> _T:
    """Alias of :func:`autowired` / :func:`autowired` 的别名。"""
    return autowired(clazz)
