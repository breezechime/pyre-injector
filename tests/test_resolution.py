"""依赖解析与获取测试。"""
import pytest

from pyre_injector import (
    DependencyContainer,
    DependencyNotInitializedError,
    autowired,
    provider,
)


def test_nested_dependencies_injected():
    class Repo:
        def __init__(self):
            self.kind = 'repo'

    class Service:
        def __init__(self, repo: Repo):
            self.repo = repo

    container = DependencyContainer()
    container.inject(Repo)
    container.inject(Service)
    container.init_dependency_container()

    service = container.provider(Service)
    assert isinstance(service, Service)
    assert isinstance(service.repo, Repo)


def test_singleton_shared_between_consumers():
    class Shared:
        pass

    class A:
        def __init__(self, shared: Shared):
            self.shared = shared

    class B:
        def __init__(self, shared: Shared):
            self.shared = shared

    container = DependencyContainer()
    for cls in (Shared, A, B):
        container.inject(cls)
    assert container.provider(A).shared is container.provider(B).shared


def test_provider_by_type_and_name():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service, depend_name='svc')
    assert container.provider('svc') is container.provider(Service)


def test_autowired_and_provider_module_functions():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service)
    container.init_dependency_container()
    assert autowired(Service) is container.provider(Service)
    assert provider(Service) is container.provider(Service)


def test_manual_instance_injection():
    class Manual:
        def __init__(self, value):
            self.value = value

    instance = Manual(7)
    container = DependencyContainer()
    container.inject(instance)
    assert container.provider(Manual) is instance
    assert container.provider('Manual') is instance


def test_manual_instance_injection_with_explicit_name():
    class Thing:
        pass

    instance = Thing()
    container = DependencyContainer()
    container.inject('custom', instance)
    assert container.provider('custom') is instance


def test_manual_instance_duplicate_raises():
    class Thing:
        pass

    container = DependencyContainer()
    container.inject(Thing())
    with pytest.raises(RuntimeError):
        container.inject(Thing())


def test_injected_instance_used_as_dependency():
    class Config:
        def __init__(self):
            self.env = 'dev'

    class Service:
        def __init__(self, config: Config):
            self.config = config

    config = Config()
    container = DependencyContainer()
    container.inject(config)
    container.inject(Service)
    assert container.provider(Service).config is config


def test_defaults_used_when_dependency_missing():
    class Service:
        def __init__(self, port: int = 8080, tag='x'):
            self.port = port
            self.tag = tag

    container = DependencyContainer()
    container.inject(Service)
    service = container.provider(Service)
    assert service.port == 8080
    assert service.tag == 'x'


def test_registered_dependency_resolved_on_demand():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service)
    # no explicit init_dependency_container() call
    assert isinstance(container.provider(Service), Service)


def test_unknown_dependency_raises():
    class Unknown:
        pass

    container = DependencyContainer()
    with pytest.raises(DependencyNotInitializedError):
        container.provider(Unknown)
    with pytest.raises(DependencyNotInitializedError):
        container.provider('nope')
