"""最小可用示例：用容器注册依赖并按类型获取。

在仓库根目录执行：``python examples/basic.py``
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyre_injector import DependencyContainer, autowired  # noqa: E402


class DatabaseConfig:
    def __init__(self):
        self.host = 'localhost'
        self.port = 5432


class UserRepository:
    def __init__(self, config: DatabaseConfig):
        self.config = config

    def find_by_id(self, user_id: int):
        return f'User {user_id} from {self.config.host}:{self.config.port}'


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def get_user(self, user_id: int):
        return self.repository.find_by_id(user_id)


def main():
    container = DependencyContainer()

    # 1) 注册依赖（推荐统一使用 container.）
    container.inject(DatabaseConfig)
    container.inject(UserRepository)
    container.inject(UserService)

    # 2) 激活容器并立即构建所有非延迟依赖
    container.init_dependency_container()

    # 3) 获取依赖
    service = container.provider(UserService)
    print('container.provider ->', service.get_user(123))

    # 也可以通过模块级 autowired 从活动容器取（框架层用法）
    print('autowired          ->', autowired(UserService).get_user(456))

    # 单例：两次取到的是同一个对象
    print('singleton shared   ->', container.provider(UserService) is service)


if __name__ == '__main__':
    main()
