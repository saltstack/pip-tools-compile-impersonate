# -*- coding: utf-8 -*-
'''
noxfile
~~~~~~~

Nox configuration script
'''

# Import Python libs
from __future__ import absolute_import, unicode_literals, print_function
import os


if __name__ == '__main__':
    sys.stderr.write('Do not execute this file directly. Use nox instead, it will know how to handle this file\n')
    sys.stderr.flush()
    exit(1)

# Import 3rd-party libs
import nox

PYTHON_VERSIONS = ('2.7', '3.4', '3.5', '3.6', '3.7', '3.8')


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    session.install('-e', '.')
    session.install('pytest')
    session.run('pytest', '-ra', '-s', '-vv', 'tests', *session.posargs)


@nox.session(python=False, name='tests-system')
def tests_system(session):
    session.install('-e', '.')
    session.install('pytest')
    session.run('pytest', '-ra', '-s', '-vv', 'tests', *session.posargs)
