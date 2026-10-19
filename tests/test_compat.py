"""框架集成兼容性测试：模拟 pyre_flask / pyre_starlette 的用法。"""
import pytest

from pyre_injector import (
    DependencyContainer,
    DependencyDefinition,
    autowired,
    provider,
)


class BaseService:
    """框架里 BaseService 通过 __init_subclass__ 自动注册依赖。"""

    model_class = None

    def __init_subclass__(cls, **kwargs):
        bean_definition = DependencyDefinition.parse_dependency(cls)
        if cls.__name__ not in DependencyContainer.dependency_definitions:
            DependencyContainer.register_dependency_definition(cls.__name__, bean_definition)
        return super().__init_subclass__(**kwargs)

    def autowired(self, name):
        return autowired(name)

    def provider(self, name):
        return provider(name)


class App:
    """占位：模拟 PyreFlask，构造函数带默认参数。"""

    def __init__(self, config_loader=None, app=None):
        self.ready = True


class AppConfig:
    def __init__(self):
        self.env = 'dev'


class Db:
    def __init__(self):
        self.engine = 'engine'


class UserRepo(BaseService):
    def __init__(self, db: Db):
        self.db = db


class UserService(BaseService):
    def __init__(self, user_repo: UserRepo):
        self.user_repo = user_repo


@pytest.fixture(autouse=True)
def framework_classes(clean_container):
    """全局注册表按测试清空后，重新登记模块级服务类。"""
    for clazz in (UserRepo, UserService):
        if clazz.__name__ not in DependencyContainer.dependency_definitions:
            DependencyContainer.register_dependency_definition(
                clazz.__name__, DependencyDefinition.parse_dependency(clazz)
            )
    yield


def test_init_subclass_auto_registration():
    class LocalService(BaseService):
        pass

    assert 'LocalService' in DependencyContainer.dependency_definitions


def test_bootstrap_like_real_app():
    container = DependencyContainer()
    app = App()
    app_config = AppConfig()
    db = Db()

    container.inject(app)
    container.inject(app_config)
    container.inject(db)
    container.init_dependency_container()

    assert autowired(UserService).user_repo.db.engine == 'engine'
    assert autowired(App) is app
    assert autowired(AppConfig) is app_config
    assert autowired('App') is app


def test_service_helpers_delegate_to_container():
    container = DependencyContainer()
    container.inject(Db())
    container.inject(App())
    container.init_dependency_container()

    service = autowired(UserService)
    assert service.autowired(UserRepo) is autowired(UserRepo)
    assert isinstance(service.provider(App), App)


def test_register_controller_style():
    class Ctrl:
        pass

    definition = DependencyDefinition.parse_dependency(Ctrl)
    DependencyContainer.register_dependency_definition('Ctrl', definition, solve_init=False)

    container = DependencyContainer()
    container.active()
    assert isinstance(autowired(Ctrl), Ctrl)
