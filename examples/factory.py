"""工厂函数注册：适合需要复杂初始化逻辑的依赖。

在仓库根目录执行：``python examples/factory.py``
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyre_injector import DependencyContainer, inject  # noqa: E402


class DatabaseConfig:
    def __init__(self):
        self.host = 'localhost'
        self.port = 5432


class Connection:
    def __init__(self, host, port):
        self.host = host
        self.port = port


def main():
    container = DependencyContainer()
    container.inject(DatabaseConfig)

    # 模块级工厂函数：返回类型注解用于确定依赖类型
    @inject(depend_name='connection')
    def create_connection(config: DatabaseConfig) -> Connection:
        return Connection(config.host, config.port)

    conn = container.provider('connection')
    print('factory connection ->', conn.host, conn.port)

    # 类内工厂方法：方法所属的类实例会作为 self 注入
    @inject
    class SessionFactory:
        def __init__(self):
            self.counter = 0

        @inject(depend_name='session')
        def create_session(self) -> Connection:
            self.counter += 1
            return Connection(f'session-{self.counter}', 0)

    session = container.provider('session')
    factory = container.provider(SessionFactory)
    print('factory method      ->', session.host, '| factory.counter =', factory.counter)


if __name__ == '__main__':
    main()
