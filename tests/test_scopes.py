"""作用域与延迟初始化测试。"""
from pyre_injector import DependencyContainer, inject


def test_singleton_is_default_scope():
    container = DependencyContainer()

    @container.inject
    class Service:
        pass

    assert container.provider(Service) is container.provider(Service)


def test_prototype_creates_new_instance():
    container = DependencyContainer()

    @container.inject(scope='prototype')
    class Service:
        pass

    assert container.provider(Service) is not container.provider(Service)


def test_prototype_dependency_not_shared():
    class Dep:
        pass

    class Consumer:
        def __init__(self, dep: Dep):
            self.dep = dep

    container = DependencyContainer()
    container.inject(Dep, scope='prototype')
    container.inject(Consumer, scope='prototype')
    assert container.provider(Consumer).dep is not container.provider(Consumer).dep


def test_lazy_dependency_not_built_until_requested():
    container = DependencyContainer()

    @container.inject(lazy_init=True)
    class Lazy:
        def __init__(self):
            self.ready = True

    container.init_dependency_container()
    assert 'Lazy' not in container.singleton_objects
    assert container.provider(Lazy).ready is True
    assert 'Lazy' in container.singleton_objects


def test_non_lazy_dependency_built_by_init():
    container = DependencyContainer()

    @container.inject
    class Eager:
        pass

    container.init_dependency_container()
    assert 'Eager' in container.singleton_objects


def test_lazy_singleton_is_shared():
    container = DependencyContainer()

    @container.inject(lazy_init=True)
    class Lazy:
        pass

    assert container.provider(Lazy) is container.provider(Lazy)


def test_scope_recorded_in_definition():
    class Proto:
        pass

    container = DependencyContainer()
    container.inject(Proto, scope='prototype')
    assert DependencyContainer.dependency_definitions['Proto'].scope == 'prototype'


def test_inject_decorator_scope_metadata():
    from pyre_injector import DependencyDefinition

    @inject(scope='prototype', lazy_init=True)
    class Service:
        pass

    definition = DependencyDefinition.parse_dependency(Service)
    assert definition.scope == 'prototype'
    assert definition.lazy_init is True
