from setuptools import setup

setup(
    name='pip-tools-compile',
    version='1.0',
    install_requires=[
        'six',
        'pip-tools==3.6.1',
        'pip==19.1',
        'setuptools-rust',
        'mock>=2.0.0; python_version < \'3\''
    ],
    scripts=['pip-tools-compile'])
