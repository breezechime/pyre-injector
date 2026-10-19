"""异常与定位信息测试。"""
import pytest

from pyre_injector import (
    DependencyAlreadyRegisteredError,
    DependencyAnnotationError,
    DependencyContainer,
    DependencyCycleError,
    DependencyError,
    DependencyInitError,
    DependencyNotInitializedError,
    DependencyNotRegisteredError,
    autowired,
)


class CycleA:
    def __init__(self, b: 'CycleB'):
        self.b = b


class CycleB:
    def __init__(self, a: CycleA):
        self.a = a


def test_init_error_reports_origin_location():
    class Broken:
        def __init__(self):
            raise ValueError('boom')

    container = DependencyContainer()
    container.inject(Broken, solve_init=False)

    with pytest.raises(DependencyInitError) as exc_info:
        container.provider(Broken)

    error = exc_info.value
    message = str(error)
    assert error.depend_name == 'Broken'
    # the origin points at the user code that actually raised
    assert error.origin and 'test_errors.py' in error.origin
    assert error.origin.endswith('(in __init__)')
    assert 'test_errors.py' in message
    assert 'boom' in message
    assert isinstance(error.__cause__, ValueError)
    assert isinstance(error, DependencyError)
    assert isinstance(error, RuntimeError)


def test_init_error_from_nested_call_reports_innermost_frame():
    def explode():
        raise KeyError('inner')

    class Broken:
        def __init__(self):
            explode()

    container = DependencyContainer()
    container.inject(Broken, solve_init=False)
    with pytest.raises(DependencyInitError) as exc_info:
        container.provider(Broken)
    assert exc_info.value.origin.endswith('(in explode)')


def test_missing_dependency_reports_required_by_location():
    class Missing:
        pass

    class Needs:
        def __init__(self, missing: Missing):
            self.missing = missing

    container = DependencyContainer()
    container.inject(Needs, solve_init=False)

    with pytest.raises(DependencyNotRegisteredError) as exc_info:
        container.provider(Needs)

    message = str(exc_info.value)
    assert 'Missing' in message
    assert "'missing'" in message
    assert 'test_errors.py' in message


def test_missing_annotation_reports_location():
    class Needs:
        def __init__(self, thing):
            self.thing = thing

    container = DependencyContainer()
    container.inject(Needs, solve_init=False)

    with pytest.raises(DependencyAnnotationError) as exc_info:
        container.provider(Needs)

    message = str(exc_info.value)
    assert "'thing'" in message
    assert 'test_errors.py' in message


def test_circular_dependency_detected():
    container = DependencyContainer()
    container.inject(CycleA, solve_init=False)
    container.inject(CycleB, solve_init=False)

    with pytest.raises(DependencyCycleError) as exc_info:
        container.provider(CycleA)

    message = str(exc_info.value)
    assert 'CycleA' in message and 'CycleB' in message
    assert '->' in message


def test_already_registered_error():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service)
    with pytest.raises(DependencyAlreadyRegisteredError):
        container.inject(Service)


def test_double_init_raises():
    class Service:
        pass

    container = DependencyContainer()
    container.inject(Service)
    container.init_dependency_container()
    with pytest.raises(DependencyError):
        container.init_dependency_container()


def test_autowired_without_active_container_raises():
    class Service:
        pass

    with pytest.raises(DependencyNotInitializedError):
        autowired(Service)


def test_not_registered_lookup_error():
    with pytest.raises(DependencyNotRegisteredError):
        DependencyContainer.get_dependency_definition('missing')
