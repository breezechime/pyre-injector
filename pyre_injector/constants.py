"""
Constants for dependency injection.
依赖注入相关常量。
"""
from typing import TypeVar, Any

# Type variable for generic types
# 泛型类型变量
_T = TypeVar("_T", bound="Any")

# Attribute keys for dependency injection metadata
# 依赖注入元数据的属性键
INJECT_SCOPE_KEY = '__pyre_scope__'  # Key for dependency scope / 依赖作用域的键
INJECT_LAZY_INIT_KEY = '__pyre_lazy_init__'  # Key for lazy initialization flag / 延迟初始化标志的键
INJECT_DEPEND_KEY = '__pyre_depend__'  # Key for marking a class as injectable / 标记类为可注入的键
INJECT_DEPEND_NAME_KEY = '__pyre_depend_name__'  # Key for custom dependency name / 自定义依赖名称的键
