import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyre_injector import DependencyContainer  # noqa: E402
from pyre_injector.globals import _active  # noqa: E402


@pytest.fixture(autouse=True)
def clean_container():
    """隔离测试之间的全局注册表与活动容器（注册表是类级共享的）。"""
    DependencyContainer.clear()
    _active.set_instance(None)
    DependencyContainer._default_instance = None
    yield
    DependencyContainer.clear()
    _active.set_instance(None)
    DependencyContainer._default_instance = None
