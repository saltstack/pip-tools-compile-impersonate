from setuptools import setup

setup(
    name="pip-tools-compile",
    version="2.0",
    install_requires=[
        "pip-tools==5.5.0",
        "pip==20.2.4",
        "setuptools-rust",
    ],
    scripts=["pip-tools-compile"],
)
