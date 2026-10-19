"""注册与容器 API 测试。"""
import pytest

from pyre_injector import (
    DependencyAlreadyRegisteredError,
    DependencyContainer,
    DependencyDefinition,
    inject,
)


def test_container_inject_registers_class():
    class Repo:
        pass

    container = DependencyContainer()
    container.inject(Repo)
    assert DependencyContainer.is_registered(Repo)
    assert DependencyContainer.is_registered('Repo')
    assert isinstance(container.provider(Repo), Repo)


def test_container_inject_works_as_decorator():
    class Service:
        pass

    container = DependencyContainer()

    @container.inject
    class Decorated:
        pass

    assert DependencyContainer.is_registered(Decorated)
    assert isinstance(container.provider(Decorated), Decorated)
    # Decorated class itself is returned unchanged
    assert isinstance(Decorated(), Decorated)


def test_container_inject_decorator_with_options():
    class Proto:
        pass

    container = DependencyContainer()

    @container.inject(scope='prototype')
    class WithOptions:
        pass

    assert container.provider(WithOptions) is not container.provider(WithOptions)


def test_module_level_inject_decorator():
    @inject
    class Service:
        pass

    container = DependencyContainer()
    container.init_dependency_container()
    assert isinstance(container.provider(Service), Service)


def test_module_level_inject_with_arguments():
    @inject(depend_name='named_service', scope='prototype')
    class Service:
        pass

    container = DependencyContainer()
    assert DependencyContainer.is_registered('named_service')
    assert container.provider('named_service') is not container.provider('named_service')


def test_duplicate_registration_raises():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service)
    with pytest.raises(DependencyAlreadyRegisteredError):
        container.inject(Service)


def test_replace_registration():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service)
    container.inject(Service, replace=True)
    assert isinstance(container.provider(Service), Service)


def test_custom_dependency_name():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service, depend_name='svc')
    assert container.provider('svc') is container.provider(Service)


def test_register_dependency_definition_classmethod():
    class Service:
        pass

    definition = DependencyDefinition.parse_dependency(Service)
    DependencyContainer.register_dependency_definition('Service', definition)
    assert 'Service' in DependencyContainer.dependency_definitions
    assert DependencyContainer.get_dependency_definition(Service)[0] == 'Service'


def test_get_dependency_definition_by_name_and_type():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service, depend_name='svc')
    assert DependencyContainer.get_dependency_definition('svc')[0] == 'svc'
    assert DependencyContainer.get_dependency_definition(Service)[0] == 'svc'


def test_clear_drops_definitions():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service)
    DependencyContainer.clear()
    assert not DependencyContainer.is_registered(Service)
