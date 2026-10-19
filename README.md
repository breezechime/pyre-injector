# pyre-injector

轻量级 Python 依赖注入框架。自动解析类型注解、管理作用域与延迟初始化，
**核心零依赖**（仅标准库），推荐统一通过 `container.` 注册与获取依赖。

```python
from pyre_injector import DependencyContainer

container = DependencyContainer()

class DatabaseConfig:
    def __init__(self):
        self.host = 'localhost'

class UserRepository:
    def __init__(self, config: DatabaseConfig):
        self.config = config

container.inject(DatabaseConfig)
container.inject(UserRepository)

container.provider(DatabaseConfig).host        # 'localhost'
container.provider(UserRepository).config      # DatabaseConfig 实例（自动注入）
```

## 特性

- **自动依赖解析** — 依据构造函数 / 工厂函数的类型注解递归装配依赖。
- **`container.` 统一 API** — `container.inject()` 注册，`container.provider()` 获取。
- **装饰器同样可用** — `@inject` / `@inject(scope='prototype')`，与容器 API 等价。
- **作用域管理** — `singleton`（默认）与 `prototype`。
- **延迟初始化** — `lazy_init=True` 时首次使用时才构建。
- **工厂函数** — 支持模块级工厂与类内工厂方法，工厂参数同样参与注入。
- **手动注入实例** — 把已构造好的对象（配置、连接池、logger……）交给容器。
- **精确的异常定位** — 初始化失败时报出**异常发生位置**与**依赖定义位置**，并检测循环依赖。
- **零必需依赖** — 只用标准库。

## 安装

```bash
pip install pyre-injector
```

## 快速开始

### 注册依赖

推荐统一使用 `container.inject(...)`：

```python
from pyre_injector import DependencyContainer

container = DependencyContainer()

container.inject(Logger)                              # 按类注册
container.inject(Cache, scope='prototype')            # 带作用域
container.inject(Mailer, depend_name='mailer')        # 自定义名称
container.inject(LazyClient, lazy_init=True)          # 延迟初始化

@container.inject                                     # 也可以当装饰器
class Metrics:
    ...
```

`@inject` 是等价的模块级写法，适合在模块导入时声明：

```python
from pyre_injector import inject

@inject
class Logger:
    ...

@inject(scope='prototype', lazy_init=True)
class Cache:
    ...
```

### 获取依赖

```python
container.provider(Logger)        # 按类型
container.provider('mailer')      # 按名称
```

`init_dependency_container()` 会激活容器并立即构建所有非延迟依赖，
此后即可在任意位置用模块级 `autowired(...)` / `provider(...)` 取用：

```python
container.init_dependency_container()

from pyre_injector import autowired, provider

autowired(Logger)      # 从活动容器按类型获取
provider('mailer')     # provider 是 autowired 的别名
```

## 作用域

| 作用域 | 说明 |
| --- | --- |
| `singleton` | 默认。整个容器生命周期内只有一个实例。 |
| `prototype` | 每次 `provider()` 都创建新实例。 |

```python
container.inject(Config)                          # singleton
container.inject(RequestContext, scope='prototype')

container.provider(Config) is container.provider(Config)                              # True
container.provider(RequestContext) is not container.provider(RequestContext)          # True
```

## 延迟初始化

非延迟依赖会在 `init_dependency_container()` 时按依赖顺序构建；
`lazy_init=True` 的依赖推迟到首次 `provider()` 时才构建。

```python
container.inject(HeavyClient, lazy_init=True)
container.init_dependency_container()   # 此时 HeavyClient 尚未构建

client = container.provider(HeavyClient)  # 这一行才真正构建
```

## 工厂函数

工厂函数需要返回类型注解，用它来确定依赖类型；工厂参数同样参与注入。

```python
from pyre_injector import inject

@inject(depend_name='connection')
def create_connection(config: DatabaseConfig) -> Connection:
    return Connection(config.host, config.port)

container.provider('connection')
```

类内工厂方法会把方法所属的类实例作为 `self` 注入：

```python
@inject
class SessionFactory:
    def __init__(self):
        self.counter = 0

    @inject(depend_name='session')
    def create_session(self) -> Session:
        self.counter += 1
        return Session(f'session-{self.counter}')
```

没有返回类型注解时可用 `return_type` 显式指定：

```python
container.inject(create_thing, return_type=Thing, depend_name='thing')
```

## 手动注入实例

已经构造好的对象可以直接交给容器，供其它依赖自动注入：

```python
container.inject(app)                       # 名称默认取 instance.__class__.__name__
container.inject('pyre_flask', app)         # 也可以显式指定名称
container.inject('app_config', AppConfig())
```

> 传类 / 工厂函数走**注册**，传实例走**手动注入**，二者共用 `container.inject(...)`。

## 自定义名称

```python
container.inject(UserService, depend_name='user_service')

container.provider('user_service') is container.provider(UserService)   # True
```

## 错误定位

初始化失败时，异常信息会同时给出**依赖定义位置**和**异常实际发生位置**：

```
DependencyInitError: Failed to initialize dependency 'BrokenService'. 初始化依赖 'BrokenService' 失败。
	└─ defined at: __main__.BrokenService (examples/errors.py:19)
	└─ origin    : examples/errors.py:21 (in __init__)
	ValueError: 数据库连接失败
```

- `defined at` — 依赖在**哪里定义/注册**（模块.类名 + 文件:行号）。
- `origin` — 异常**实际抛出**的位置（最内层用户代码帧），原始异常通过 `__cause__` 保留。
- `DependencyInitError.origin` 与 `.depend_name` 两个属性可直接读取，便于上报与断言。

### 异常类型

| 异常 | 触发场景 |
| --- | --- |
| `DependencyInitError` | 构造函数 / 工厂函数抛出异常（含 `origin` 定位）。 |
| `DependencyNotRegisteredError` | 参数声明的类型未注册，或按名称/类型查不到定义。 |
| `DependencyAnnotationError` | 参数缺少类型注解，且无默认值。 |
| `DependencyCycleError` | 检测到循环依赖，消息中给出完整链路。 |
| `DependencyAlreadyRegisteredError` | 同名依赖重复注册 / 重复注入（可用 `replace=True` 覆盖）。 |
| `DependencyNotInitializedError` | 从活动容器取值但容器未激活，或名称未注册。 |

全部异常都继承自 `DependencyError`，而 `DependencyError` 继承自 `RuntimeError`。

```python
from pyre_injector import DependencyContainer, DependencyInitError

try:
    container.provider(BrokenService)
except DependencyInitError as error:
    print(error.origin)       # 'app/services.py:21 (in __init__)'
    print(error.__cause__)    # 原始异常
```

## 与 Web 框架集成

`pyre-injector` 不依赖任何 Web 框架。框架侧通常按下面三步接入：

1. 创建 `DependencyContainer`；
2. 用 `container.inject(...)` 注册服务，把 app / config / logger / db 等实例手动注入；
3. 调用 `container.init_dependency_container()` 激活容器，之后框架反射注入时统一用 `autowired(...)` 取值。

```python
container = DependencyContainer()
container.inject(app)
container.inject(app_config)
container.inject(logger)
container.inject(DatabaseConfig)
container.init_dependency_container()
```

框架里的服务基类也可以走等价的类方法式注册：

```python
from pyre_injector import DependencyContainer, DependencyDefinition, autowired


class BaseService:
    def __init_subclass__(cls, **kwargs):
        definition = DependencyDefinition.parse_dependency(cls)
        if cls.__name__ not in DependencyContainer.dependency_definitions:
            DependencyContainer.register_dependency_definition(cls.__name__, definition)
        return super().__init_subclass__(**kwargs)

    def autowired(self, name):
        return autowired(name)
```

## API 参考

| 名称 | 说明 |
| --- | --- |
| `DependencyContainer` | 容器。`inject` / `provider` / `inject_instance` / `init_dependency_container` / `active` / `clear` / `is_registered` / `register_dependency_definition` / `get_dependency_definition` / `solve_depend_init` |
| `DependencyDefinition` | 依赖定义。`parse_dependency()` / `depend_class` / `depend_func` / `scope` / `lazy_init` / `depends_on` |
| `inject` | 模块级注册装饰器，等价于 `container.inject`。 |
| `autowired` / `provider` | 从活动容器按类型或名称获取依赖（两者等价）。 |
| `DependencyError` | 所有异常基类（`RuntimeError` 子类）。 |
| `DependencyInitError` | 初始化失败，带 `origin` / `depend_name`。 |
| `DependencyNotRegisteredError` / `DependencyAnnotationError` / `DependencyCycleError` / `DependencyAlreadyRegisteredError` / `DependencyNotInitializedError` | 具体错误类型。 |

### `container.inject`

```python
container.inject(
    target=None,               # 类 / 工厂函数（注册）或实例（手动注入）
    depend_instance=None,
    *,
    name=None,                 # 手动注入时的名称
    depend_name=None,          # 注册时使用的名称，默认取类名
    scope=None,                # 'singleton' | 'prototype'
    lazy_init=None,            # 是否延迟初始化
    return_type=None,          # 工厂函数的返回类型
    solve_init=True,           # 注册后若容器已就绪是否立即构建
    replace=False,             # 是否覆盖同名定义
)
```

### `container.provider`

```python
container.provider(name)       # name: 类 / 工厂函数 / 字符串名称
```

## 开发

```bash
pip install -e . pytest
pytest tests -q
```

示例位于 `examples/`：

```bash
python examples/basic.py          # 最小可用
python examples/container_api.py  # 推荐用法：container.inject / provider
python examples/scopes.py         # 作用域与延迟初始化
python examples/factory.py        # 工厂函数 / 工厂方法
python examples/errors.py         # 异常与定位信息
```

## 许可

本项目基于 [MIT](LICENSE) 许可开源。
