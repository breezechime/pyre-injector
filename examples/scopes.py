"""作用域与延迟初始化。

在仓库根目录执行：``python examples/scopes.py``
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyre_injector import DependencyContainer  # noqa: E402


class SingletonService:
    def __init__(self):
        print('  SingletonService 构建')


class PrototypeService:
    def __init__(self):
        print('  PrototypeService 构建')


class LazyService:
    def __init__(self):
        print('  LazyService 构建')


def main():
    container = DependencyContainer()

    container.inject(SingletonService)                       # 默认 singleton
    container.inject(PrototypeService, scope='prototype')    # 每次新建
    container.inject(LazyService, lazy_init=True)            # 首次使用时才构建

    print('init_dependency_container():')
    container.init_dependency_container()

    print('singleton 两次获取是同一个对象:', container.provider(SingletonService) is container.provider(SingletonService))
    print('prototype 两次获取是新对象  :', container.provider(PrototypeService) is not container.provider(PrototypeService))

    print('lazy 在首次 provider 时才构建:')
    container.provider(LazyService)


if __name__ == '__main__':
    main()
