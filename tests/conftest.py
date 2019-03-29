# -*- coding: utf-8 -*-
'''
conftest
~~~~~~~~
'''

# Import Python Libs
import os
import sys
import logging
import subprocess
from collections import namedtuple

# Import 3rd-party libs
import pytest

REPO_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

ProcessResult = namedtuple('ProcessResult', ['rc', 'stdout', 'stderr'])
log = logging.getLogger(__name__)


class RunCommand(object):
    def __init__(self):
        self.argv = [
            #sys.executable,
        ]
        self.environ = os.environ.copy()
        self.environ['CAPTURE_OUTPUT'] = '0'

    def __call__(self, *args):
        cmdline = self.argv + list(args)
        log.info('Running: %r', ' '.join(cmdline))
        try:
            return subprocess.check_call(cmdline, cwd=REPO_ROOT, env=self.environ)
        except subprocess.CalledProcessError as exc:
            return exc.returncode


@pytest.fixture
def run_command():
    return RunCommand()
