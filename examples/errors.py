"""错误与定位：每次初始化失败都会给出「依赖定义位置」与「异常发生位置」。

在仓库根目录执行：``python examples/errors.py``
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyre_injector import (  # noqa: E402
    DependencyContainer,
    DependencyCycleError,
    DependencyInitError,
    DependencyNotRegisteredError,
)


class BrokenService:
    def __init__(self):
        raise ValueError('数据库连接失败')


class MissingDependency:
    def __init__(self, config: 'NotRegisteredConfig'):
        self.config = config


class NotRegisteredConfig:
    pass


class CycleA:
    def __init__(self, b: 'CycleB'):
        self.b = b


class CycleB:
    def __init__(self, a: CycleA):
        self.a = a


def show(title, error):
    print(f'--- {title} ---')
    print(type(error).__name__ + ':')
    for line in str(error).splitlines():
        print('   ' + line)
    print()


def main():
    container = DependencyContainer()

    # 1) 构造函数抛异常：报出异常发生的文件:行号
    container.inject(BrokenService, solve_init=False)
    try:
        container.provider(BrokenService)
    except DependencyInitError as error:
        show('构造函数抛异常', error)
        print('   error.origin =', error.origin)
        print()

    # 2) 依赖未注册：报出是哪个参数、在哪个类上需要它
    container.inject(MissingDependency, solve_init=False)
    try:
        container.provider(MissingDependency)
    except DependencyNotRegisteredError as error:
        show('依赖未注册', error)

    # 3) 循环依赖：报出完整链路
    container.inject(CycleA, solve_init=False)
    container.inject(CycleB, solve_init=False)
    try:
        container.provider(CycleA)
    except DependencyCycleError as error:
        show('循环依赖', error)


if __name__ == '__main__':
    main()
