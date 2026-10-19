"""
Dependency injection container.
依赖注入容器。
"""
from functools import wraps
import inspect
import os
import typing
from types import FunctionType
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Tuple, Type, Union

from .constants import _T, INJECT_DEPEND_KEY, INJECT_DEPEND_NAME_KEY, INJECT_LAZY_INIT_KEY, INJECT_SCOPE_KEY

__all__ = [
    'DependencyError',
    'DependencyNotRegisteredError',
    'DependencyAlreadyRegisteredError',
    'DependencyNotInitializedError',
    'DependencyInitError',
    'DependencyAnnotationError',
    'DependencyCycleError',
    'DependencyDefinition',
    'DependencyContainer',
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class DependencyError(RuntimeError):
    """Base class for every dependency-injection error.

    继承自 ``RuntimeError``，保持对旧版本 ``except RuntimeError`` 的兼容。
    """


class DependencyNotRegisteredError(DependencyError):
    """The requested dependency has no registered definition."""


class DependencyAlreadyRegisteredError(DependencyError):
    """Two definitions were registered under the same name."""


class DependencyNotInitializedError(DependencyError):
    """The dependency is registered but its instance is not available yet."""


class DependencyAnnotationError(DependencyError):
    """A constructor / factory parameter has no usable type annotation."""


class DependencyCycleError(DependencyError):
    """A circular dependency chain was detected."""


class DependencyInitError(DependencyError):
    """A constructor or factory raised while a dependency was being built.

    Attributes:
        depend_name: Name of the dependency that failed to initialize.
        origin: ``relative/path.py:line (in func)`` of the innermost user frame.
    """

    def __init__(self, message: str, depend_name: Optional[str] = None, origin: Optional[str] = None):
        super().__init__(message)
        self.depend_name = depend_name
        self.origin = origin


# ---------------------------------------------------------------------------
# Source location helpers
# ---------------------------------------------------------------------------
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def _relpath(path: Optional[str]) -> str:
    """Best-effort relative path for readable messages."""
    if not path:
        return '<unknown>'
    try:
        return os.path.relpath(path)
    except (TypeError, ValueError):
        return path


def _is_internal(filename: Optional[str]) -> bool:
    """True when the frame belongs to pyre_injector itself."""
    if not filename:
        return True
    try:
        return os.path.abspath(filename).startswith(_PACKAGE_DIR)
    except (TypeError, ValueError):
        return True


def _type_name(annotation: Any) -> str:
    """Human readable name for a type / typing form / arbitrary object."""
    if annotation is inspect.Parameter.empty:
        return '<empty>'
    module = getattr(annotation, '__module__', None)
    qualname = getattr(annotation, '__qualname__', None) or getattr(annotation, '__name__', None)
    if qualname:
        return f'{module}.{qualname}' if module else qualname
    return str(annotation)


def describe_target(target: Any) -> str:
    """Describe a class / factory as ``module.qualname (relative/path.py:line)``.

    依赖定义的位置信息，用于异常信息中定位「是在哪里注册/定义的」。
    """
    if target is None:
        return '<unknown>'
    func = getattr(target, '__func__', target)
    module = getattr(func, '__module__', None)
    qualname = getattr(func, '__qualname__', None) or getattr(func, '__name__', None) or repr(func)
    label = f'{module}.{qualname}' if module else str(qualname)

    file = None
    line = None
    try:
        file = inspect.getsourcefile(func) or inspect.getfile(func)
    except (TypeError, OSError):
        file = getattr(getattr(func, '__code__', None), 'co_filename', None)
    if file:
        try:
            _, line = inspect.getsourcelines(func)
        except (TypeError, OSError):
            line = None
    if file and line:
        return f'{label} ({_relpath(file)}:{line})'
    if file:
        return f'{label} ({_relpath(file)})'
    return label


def describe_exception(exc: BaseException) -> Tuple[str, Optional[str]]:
    """Locate the innermost non-pyre_injector frame of ``exc``.

    返回 ``(文本描述, 文件路径)``，例如 ``('app.py:42 (in __init__)', 'D:/.../app.py')``。
    这就是「异常实际发生的位置」，而不是容器内部的调用点。
    """
    traceback = exc.__traceback__
    origin: Optional[Tuple[str, int, str]] = None
    while traceback is not None:
        filename = traceback.tb_frame.f_code.co_filename
        if not _is_internal(filename):
            origin = (filename, traceback.tb_lineno, traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    if origin is None:
        return '', None
    filename, lineno, func_name = origin
    return f'{_relpath(filename)}:{lineno} (in {func_name})', filename


def _type_hints(target: Any) -> Dict[str, Any]:
    """Resolve annotations, tolerating ``from __future__ import annotations``."""
    try:
        return typing.get_type_hints(target)
    except Exception:
        return dict(getattr(target, '__annotations__', None) or {})


class _DualMethod:
    """Bind a plain function to both the class and its instances.

    让 ``DependencyContainer.inject(...)`` 与 ``container.inject(...)`` 都能工作：
    前者用于注册依赖，后者既可注册依赖，也可注入现成实例。
    """

    def __init__(self, func: Callable):
        self._func = func
        try:
            wraps(func)(self)
        except Exception:  # pragma: no cover - defensive
            pass

    def __get__(self, instance, owner=None):
        bound = instance if instance is not None else owner

        @wraps(self._func)
        def wrapper(*args, **kwargs):
            return self._func(bound, *args, **kwargs)

        return wrapper


# ---------------------------------------------------------------------------
# Dependency definition
# ---------------------------------------------------------------------------
class DependencyDefinition(Generic[_T]):
    """Metadata describing a single dependency.
    描述单个依赖的元数据：类型、工厂函数、作用域与延迟初始化标记。
    """

    depend_class: Type[_T]
    depend_func: Optional[Callable]
    scope: str
    lazy_init: bool
    depends_on: List[str]

    def __init__(self) -> None:
        self.depend_class = None
        self.depend_func = None
        self.scope = 'singleton'
        self.lazy_init = False
        self.depends_on = []

    @classmethod
    def parse_dependency(cls, clazz: Type[_T], depend_func: Optional[Callable] = None) -> "DependencyDefinition[_T]":
        """Build a definition from a class, reading ``@inject`` metadata."""
        definition = cls()
        definition.depend_class = clazz
        definition.depend_func = depend_func
        definition.scope = getattr(clazz, INJECT_SCOPE_KEY, None) or 'singleton'
        definition.lazy_init = getattr(clazz, INJECT_LAZY_INIT_KEY, False) is True
        definition.depends_on = []
        return definition

    @property
    def factory(self) -> Callable:
        """Callable used to create the instance."""
        return self.depend_func or self.depend_class

    def __repr__(self):
        return (f"{self.__class__.__name__}("
                f"depend_class={getattr(self.depend_class, '__name__', self.depend_class)}, "
                f"depend_func={getattr(self.depend_func, '__name__', self.depend_func)}, "
                f"scope={self.scope!r}, "
                f"lazy_init={self.lazy_init}, "
                f"depends_on={self.depends_on!r})")


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------
class DependencyContainer:
    """Dependency injection container.
    依赖注入容器：管理依赖的注册、解析与生命周期。
    """

    # Registered definitions, shared by every container of this class.
    # 已注册的依赖定义，由该类的所有容器实例共享。
    dependency_definitions: Dict[str, DependencyDefinition] = {}
    _default_instance: Optional["DependencyContainer"] = None

    def __init__(self) -> None:
        self._inited_factory: bool = False
        self.singleton_objects: Dict[str, Any] = {}
        self._resolving: List[str] = []
        if DependencyContainer._default_instance is None:
            DependencyContainer._default_instance = self

    # -- registry -----------------------------------------------------------
    @classmethod
    def clear(cls) -> None:
        """Drop every registered definition (tests / re-bootstrap).
        清空已注册的依赖定义。
        """
        cls.dependency_definitions.clear()

    @classmethod
    def is_registered(cls, name: Union[str, type]) -> bool:
        """Whether ``name`` (or a type) has a registered definition."""
        if isinstance(name, str):
            return name in cls.dependency_definitions
        return any(
            definition.depend_class is name or definition.depend_func is name
            for definition in cls.dependency_definitions.values()
        )

    @classmethod
    def get_dependency_definition(cls, name: Union[str, type]) -> Tuple[str, DependencyDefinition]:
        """Look a definition up by name or by class / factory identity."""
        if isinstance(name, str):
            definition = cls.dependency_definitions.get(name)
            if definition is None:
                raise DependencyNotRegisteredError(
                    f"Dependency '{name}' is not registered. "
                    f"依赖 '{name}' 未注册。"
                    f" Register it with @inject or container.inject()."
                )
            return name, definition

        for registered_name, definition in cls.dependency_definitions.items():
            if definition.depend_class is name or definition.depend_func is name:
                return registered_name, definition

        raise DependencyNotRegisteredError(
            f"Dependency '{_type_name(name)}' is not registered. "
            f"依赖 '{_type_name(name)}' 未注册。"
            f" Register it with @inject or container.inject()."
        )

    @classmethod
    def register_dependency_definition(
        cls,
        depend_name: str,
        depend_definition: DependencyDefinition,
        solve_init: bool = True,
        replace: bool = False,
    ) -> None:
        """Register a definition under ``depend_name``."""
        if depend_name in cls.dependency_definitions and not replace:
            existing = cls.dependency_definitions[depend_name]
            raise DependencyAlreadyRegisteredError(
                f"Dependency '{depend_name}' is already registered by "
                f"{describe_target(existing.factory)}. "
                f"依赖 '{depend_name}' 已注册，无法重复注册。"
                f"\n\t└─ pass replace=True to override."
            )
        if depend_definition.depend_class is not None:
            setattr(depend_definition.depend_class, INJECT_DEPEND_KEY, True)
        cls.dependency_definitions[depend_name] = depend_definition

        from .globals import _active
        container = _active.instance
        if (container is not None
                and solve_init
                and not depend_definition.lazy_init
                and container._inited_factory):
            container.solve_depend_init(depend_name, depend_definition)

    @classmethod
    def _register(
        cls,
        clazz: Union[Type[_T], Callable],
        depend_name: Optional[str] = None,
        scope: Optional[str] = None,
        lazy_init: Optional[bool] = None,
        return_type: Optional[Type[type]] = None,
        solve_init: bool = True,
        replace: bool = False,
    ) -> Any:
        """Normalise a class / factory into a definition and register it."""
        name = depend_name or getattr(clazz, INJECT_DEPEND_NAME_KEY, None) or getattr(clazz, '__name__', None)
        if not name:
            raise DependencyError(
                f"Cannot register {clazz!r}: a dependency name is required. "
                f"无法注册 {clazz!r}：缺少依赖名称。"
            )

        depend_func = None
        target = clazz
        if isinstance(clazz, FunctionType):
            depend_class = return_type or _type_hints(clazz).get('return')
            if not depend_class:
                raise DependencyAnnotationError(
                    f"Factory function {describe_target(clazz)} must declare a return type annotation, "
                    f"e.g. def factory() -> YourClass: . "
                    f"工厂函数 {describe_target(clazz)} 必须声明返回类型注解。"
                )
            setattr(clazz, INJECT_DEPEND_KEY, True)
            setattr(clazz, INJECT_DEPEND_NAME_KEY, name)
            depend_func = clazz
            target = depend_class
        else:
            # Link factory methods declared inside the class to their owner.
            for member_name in dir(clazz):
                if member_name.startswith('_'):
                    continue
                member = getattr(clazz, member_name, None)
                if callable(member) and getattr(member, INJECT_DEPEND_KEY, False):
                    member_key = getattr(member, INJECT_DEPEND_NAME_KEY, None) or member_name
                    member_definition = cls.dependency_definitions.get(member_key)
                    if member_definition is not None and clazz.__name__ not in member_definition.depends_on:
                        member_definition.depends_on.append(clazz.__name__)

        setattr(target, INJECT_DEPEND_KEY, True)
        setattr(target, INJECT_SCOPE_KEY, scope)
        setattr(target, INJECT_LAZY_INIT_KEY, lazy_init)
        definition = DependencyDefinition.parse_dependency(target, depend_func)
        cls.register_dependency_definition(name, definition, solve_init=solve_init, replace=replace)
        return clazz

    # -- decorator / manual injection --------------------------------------
    @_DualMethod
    def inject(
        holder,
        target: Any = None,
        depend_instance: Any = None,
        *,
        name: Optional[str] = None,
        depend_name: Optional[str] = None,
        scope: Optional[str] = None,
        lazy_init: Optional[bool] = None,
        return_type: Optional[Type[type]] = None,
        solve_init: bool = True,
        replace: bool = False,
    ) -> Any:
        """Register a dependency, or inject a ready-made instance.
        注册依赖或注入现成实例——推荐统一通过 ``container.inject(...)`` 使用。

        - ``container.inject(MyService)`` / ``@container.inject`` → 注册类。
        - ``container.inject(MyService, scope='prototype')`` / ``@container.inject(lazy_init=True)`` → 带参数注册。
        - ``container.inject(instance)`` / ``container.inject('name', instance)`` → 手动注入实例。
        """
        container = holder if isinstance(holder, DependencyContainer) else None
        owner_class = holder if isinstance(holder, type) else type(holder)
        look_name = depend_name or name

        # @inject(...) / @container.inject(...) -> decorator factory
        if target is None and depend_instance is None:
            def decorator(clazz: Any) -> Any:
                return owner_class.inject(
                    clazz,
                    depend_name=look_name,
                    scope=scope,
                    lazy_init=lazy_init,
                    return_type=return_type,
                    solve_init=solve_init,
                    replace=replace,
                )
            return decorator

        registrable = isinstance(target, (type, FunctionType))

        # manual instance injection
        if depend_instance is not None or not registrable:
            if depend_instance is None:
                depend_instance = target
                inject_name = look_name or depend_instance.__class__.__name__
            else:
                if not isinstance(target, str):
                    raise DependencyError(
                        "The dependency name must be a str when injecting an instance. "
                        "注入实例时依赖名称必须是字符串。"
                    )
                inject_name = target
            container = container or DependencyContainer._current()
            if container is None:
                raise DependencyError(
                    "No active DependencyContainer, cannot inject an instance. "
                    "当前没有活动的依赖容器，无法注入实例。"
                )
            container.inject_instance(inject_name, depend_instance)
            return depend_instance

        # registration
        return owner_class._register(
            target,
            depend_name=look_name,
            scope=scope,
            lazy_init=lazy_init,
            return_type=return_type,
            solve_init=solve_init,
            replace=replace,
        )

    def inject_instance(self, depend_name: str, depend_instance: Any) -> Any:
        """Manually inject a pre-built instance under ``depend_name``."""
        if depend_name in self.singleton_objects:
            raise DependencyAlreadyRegisteredError(
                f"Dependency '{depend_name}' is already injected. "
                f"依赖 '{depend_name}' 已注入，无法重复注入。"
            )
        if depend_name not in self.dependency_definitions:
            definition = DependencyDefinition()
            definition.depend_class = type(depend_instance)
            definition.depend_func = None
            definition.scope = 'singleton'
            definition.lazy_init = False
            definition.depends_on = []
            self.register_dependency_definition(depend_name, definition, solve_init=False)
        self.singleton_objects[depend_name] = depend_instance
        return depend_instance

    # -- resolution ---------------------------------------------------------
    def provider(self, name: Union[Type[_T], str, type]) -> _T:
        """Return the instance registered under ``name`` (or by type)."""
        if isinstance(name, str):
            return self._provide_by_name(name)

        # Prefer an already-injected instance (covers subclasses and aliases).
        if isinstance(name, type):
            for registered_name, instance in list(self.singleton_objects.items()):
                if isinstance(instance, name):
                    registered_definition = self.dependency_definitions.get(registered_name)
                    if registered_definition is not None and registered_definition.scope == 'prototype':
                        return self.solve_depend_init(registered_name, registered_definition, force=True)
                    return instance

        registered_name = self._registered_name(name)
        if registered_name is not None:
            return self._provide_by_name(registered_name)

        raise DependencyNotInitializedError(
            f"Dependency '{_type_name(name)}' is not initialized. "
            f"依赖 '{_type_name(name)}' 未初始化。"
            f" Register it with @inject or container.inject()."
        )

    def _registered_name(self, target: Any) -> Optional[str]:
        """Name of the definition registered for a class / factory, if any."""
        for registered_name, definition in self.dependency_definitions.items():
            if definition.depend_class is target or definition.depend_func is target:
                return registered_name
        return None

    def _provide_by_name(self, name: str) -> Any:
        definition = self.dependency_definitions.get(name)
        if definition is not None:
            if name in self.singleton_objects and definition.scope != 'prototype':
                return self.singleton_objects[name]
            # resolve on demand; lazy_init only controls eager init during init_dependency_container()
            return self.solve_depend_init(name, definition, force=definition.scope == 'prototype')
        if name in self.singleton_objects:
            return self.singleton_objects[name]
        raise DependencyNotInitializedError(
            f"Dependency '{name}' is not registered. "
            f"依赖 '{name}' 未注册。"
            f" Register it with @inject or container.inject()."
        )

    # -- construction -------------------------------------------------------
    def _iter_injectable_params(
        self,
        depend_name: str,
        depend_definition: DependencyDefinition,
        target: Optional[Callable] = None,
    ) -> Iterator[Tuple[str, Any, bool, Any]]:
        """Yield ``(param_name, annotation, has_default, default)`` for injectable params."""
        target = target or depend_definition.factory
        is_function = inspect.isfunction(target) or inspect.ismethod(target)
        if is_function:
            parameters = list(inspect.signature(target).parameters.values())
            hints = _type_hints(target)
        else:
            parameters = list(inspect.signature(target.__init__).parameters.values())
            hints = _type_hints(target.__init__)

        owner_class = None
        if is_function and depend_definition.depends_on:
            owner_definition = self.dependency_definitions.get(depend_definition.depends_on[0])
            if owner_definition is not None:
                owner_class = owner_definition.depend_class

        for index, parameter in enumerate(parameters):
            if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if index == 0 and (not is_function or parameter.name in ('self', 'cls')):
                # ``self`` of a class constructor / method; a factory method may want its owner.
                if parameter.name == 'self' and owner_class is not None:
                    yield parameter.name, owner_class, False, inspect.Parameter.empty
                continue
            annotation = hints.get(parameter.name, parameter.annotation)
            has_default = parameter.default is not inspect.Parameter.empty
            yield parameter.name, annotation, has_default, parameter.default

    def get_depend_require_depends(
        self,
        depend_name: str,
        depend_definition: DependencyDefinition,
        target: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Return ``{param_name: annotation}`` for the dependencies a target needs."""
        target = target or depend_definition.factory
        required: Dict[str, Any] = {}
        for param_name, annotation, has_default, _default in self._iter_injectable_params(
            depend_name, depend_definition, target
        ):
            if annotation is inspect.Parameter.empty:
                if has_default:
                    continue
                raise DependencyAnnotationError(
                    f"Parameter '{param_name}' of {describe_target(target)} must declare a type annotation. "
                    f"{describe_target(target)} 的参数 '{param_name}' 必须声明类型注解，"
                    f"例如：{param_name}: YourClass"
                )
            required[param_name] = annotation
        return required

    def solve_depend_init(
        self,
        depend_name: str,
        depend_definition: DependencyDefinition,
        force: bool = False,
    ) -> Any:
        """Create (or reuse) the instance of ``depend_name``, resolving its dependencies."""
        if not force and depend_name in self.singleton_objects:
            return self._provide_by_name(depend_name)

        if depend_name in self._resolving:
            chain = ' -> '.join(self._resolving + [depend_name])
            raise DependencyCycleError(
                f"Circular dependency detected: {chain}\n"
                f"检测到循环依赖：{chain}"
            )

        target = depend_definition.factory
        init_kwargs: Dict[str, Any] = {}
        self._resolving.append(depend_name)
        try:
            for param_name, annotation, has_default, _default in self._iter_injectable_params(
                depend_name, depend_definition, target
            ):
                if annotation is inspect.Parameter.empty:
                    if has_default:
                        continue
                    raise DependencyAnnotationError(
                        f"Parameter '{param_name}' of {describe_target(target)} must declare a type annotation. "
                        f"{describe_target(target)} 的参数 '{param_name}' 必须声明类型注解，"
                        f"例如：{param_name}: YourClass"
                    )
                try:
                    required_name, required_definition = self.get_dependency_definition(annotation)
                except DependencyNotRegisteredError:
                    if has_default:
                        continue
                    raise DependencyNotRegisteredError(
                        f"Dependency '{_type_name(annotation)}' is not registered, "
                        f"but it is required by parameter '{param_name}' of {describe_target(target)}. "
                        f"依赖 '{_type_name(annotation)}' 未注册，"
                        f"被 {describe_target(target)} 的参数 '{param_name}' 依赖。"
                        f"\n\t└─ add @inject / container.inject() to '{_type_name(annotation)}'."
                    )
                init_kwargs[param_name] = self.solve_depend_init(
                    required_name,
                    required_definition,
                    force=required_definition.scope == 'prototype',
                )

            try:
                instance = target(**init_kwargs)
            except DependencyError:
                raise
            except Exception as exc:
                origin_text, _origin_file = describe_exception(exc)
                origin_line = f"\n\t└─ origin    : {origin_text}" if origin_text else ''
                raise DependencyInitError(
                    f"Failed to initialize dependency '{depend_name}'. "
                    f"初始化依赖 '{depend_name}' 失败。"
                    f"\n\t└─ defined at: {describe_target(target)}"
                    f"{origin_line}"
                    f"\n\t{type(exc).__name__}: {exc}",
                    depend_name=depend_name,
                    origin=origin_text or None,
                ) from exc

            if depend_name not in self.singleton_objects:
                self.singleton_objects[depend_name] = instance
            return instance
        finally:
            self._resolving.pop()

    # -- lifecycle ----------------------------------------------------------
    def init_dependency_container(self) -> "DependencyContainer":
        """Activate this container and build every non-lazy dependency."""
        if self._inited_factory:
            raise DependencyError(
                f"{self.__class__.__name__} is already initialized. "
                f"{self.__class__.__name__} 已初始化，请勿重复初始化依赖容器。"
            )
        self.active()
        for depend_name, depend_definition in list(self.dependency_definitions.items()):
            if not depend_definition.lazy_init:
                self.solve_depend_init(depend_name, depend_definition)
        self._inited_factory = True
        return self

    def active(self) -> "DependencyContainer":
        """Make this container the process-wide active one."""
        from .globals import _active
        _active.set_instance(self)
        return self

    @classmethod
    def _current(cls) -> Optional["DependencyContainer"]:
        from .globals import _active
        return _active.instance or cls._default_instance
