"""工厂函数注册测试。"""
import pytest

from pyre_injector import (
    DependencyAnnotationError,
    DependencyContainer,
    inject,
)


def test_factory_function_with_parameters():
    class Config:
        def __init__(self):
            self.host = 'localhost'

    class Connection:
        def __init__(self, host):
            self.host = host

    container = DependencyContainer()
    container.inject(Config)

    @inject(depend_name='connection')
    def create_connection(config: Config) -> Connection:
        return Connection(config.host)

    assert container.provider('connection').host == 'localhost'


def test_factory_function_without_parameters():
    class Thing:
        def __init__(self):
            self.ok = True

    container = DependencyContainer()

    @inject
    def create_thing() -> Thing:
        return Thing()

    assert container.provider(Thing).ok is True


def test_factory_return_type_via_argument():
    class Thing:
        pass

    container = DependencyContainer()

    @container.inject(return_type=Thing)
    def create_thing():
        return Thing()

    assert isinstance(container.provider(Thing), Thing)


def test_factory_without_return_annotation_raises():
    with pytest.raises(DependencyAnnotationError):

        @inject
        def create_something():
            return object()


def test_factory_method_inside_inject_class():
    class Made:
        def __init__(self, holder):
            self.holder = holder

    @inject
    class Holder:
        @inject(depend_name='made')
        def make(self) -> Made:
            return Made(self)

    container = DependencyContainer()
    made = container.provider('made')
    assert isinstance(made, Made)
    assert isinstance(made.holder, Holder)


def test_factory_result_is_singleton():
    class Thing:
        pass

    container = DependencyContainer()

    @inject(depend_name='thing')
    def create_thing() -> Thing:
        return Thing()

    assert container.provider('thing') is container.provider(Thing)
