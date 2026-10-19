"""推荐用法：统一通过 ``container.`` 注册（inject）与获取（provider）。

在仓库根目录执行：``python examples/container_api.py``
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyre_injector import DependencyContainer  # noqa: E402


class Logger:
    def log(self, message: str):
        print(f'[log] {message}')


class Cache:
    def __init__(self):
        self.data = {}


class UserService:
    def __init__(self, logger: Logger, cache: Cache):
        self.logger = logger
        self.cache = cache


def main():
    container = DependencyContainer()

    # 直接注册
    container.inject(Logger)

    # 也可以当装饰器用
    @container.inject
    class Mailer:
        def send(self, to: str):
            print(f'[mail] -> {to}')

    # 带参数注册
    container.inject(Cache, scope='prototype')

    # 用自定义名称注册，之后按类或按名称都能取到同一个实例
    container.inject(UserService, depend_name='user_service')

    logger = container.provider(Logger)
    service = container.provider('user_service')
    service.logger.log('hello')

    # 手动注入一个现成实例
    container.inject(Mailer())
    print('manual instance    ->', container.provider(Mailer) is not None)

    # 原型作用域：每次获取都是新对象
    print('prototype is new   ->', container.provider(Cache) is not container.provider(Cache))

    # 类型 / 名称 / 类本身三种取法等价
    print('by type == by name ->', container.provider(UserService) is container.provider('user_service'))


if __name__ == '__main__':
    main()
