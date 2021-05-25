"""
noxfile
~~~~~~~

Nox configuration script
"""
import sys

if __name__ == "__main__":
    sys.stderr.write(
        "Do not execute this file directly. Use nox instead, it will know how to handle this file\n"
    )
    sys.stderr.flush()
    exit(1)

import nox

PYTHON_VERSIONS = ("3", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10")

# Nox options
#  Reuse existing virtualenvs
nox.options.reuse_existing_virtualenvs = True
#  Don't fail on missing interpreters
nox.options.error_on_missing_interpreters = False


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    session.run("python", "-m", "pip", "install", ".")
    session.install("pytest")
    session.run("python", "-m", "pytest", "-ra", "-s", "-vv", *session.posargs)


@nox.session(python=False, name="tests-system")
def tests_system(session):
    session.run("python", "-m", "pip", "install", ".")
    session.run("python", "-m", "pip", "install", "pytest")
    session.run("python", "-m", "pytest", "-ra", "-s", "-vv", "tests", *session.posargs)


@nox.session(name="patch-info", python="3")
def patch_info(session):
    session.run("python", "-m", "pip", "install", ".")
    session.run("pip-tools-compile", "--show-info-to-patch")


@nox.session(name="patch-info-system", python=False)
def patch_info_system(session):
    session.run("python", "-m", "pip", "install", ".")
    session.run("pip-tools-compile", "--show-info-to-patch")
