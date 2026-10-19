from setuptools import find_packages, setup

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pyre-injector',
    version='1.0.0',
    author='且听风吟、我是指针*、ZDLAY、KYZ',
    author_email='breezechime@163.com',
    description='轻量级 Python 依赖注入框架：自动依赖解析、作用域管理、延迟初始化，核心零依赖',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/breezechime/pyre-injector',
    project_urls={
        'Source': 'https://github.com/breezechime/pyre-injector',
        'Issues': 'https://github.com/breezechime/pyre-injector/issues',
    },
    license='MIT',
    packages=find_packages(exclude=('tests', 'tests.*', 'examples', 'examples.*')),
    package_data={'pyre_injector': ['py.typed']},
    include_package_data=True,
    python_requires='>=3.9',
    install_requires=[],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Software Distribution',
    ],
    keywords='dependency-injection di ioc container inject autowired singleton prototype',
)
