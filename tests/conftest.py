"""
conftest
~~~~~~~~
"""
import logging
import os
import subprocess
import sys
from collections import namedtuple

import pytest

REPO_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

ProcessResult = namedtuple("ProcessResult", ["rc", "stdout", "stderr"])
log = logging.getLogger(__name__)


class RunCommand:
    def __init__(self):
        self.argv = [
            # sys.executable,
        ]
        self.environ = os.environ.copy()
        self.environ["CAPTURE_OUTPUT"] = "1"

    def __call__(self, *args):
        cmdline = self.argv + list(args)
        log.info("Running: %r", " ".join(cmdline))
        try:
            return subprocess.check_call(cmdline, cwd=REPO_ROOT, env=self.environ)
        except subprocess.CalledProcessError as exc:
            return exc.returncode


@pytest.fixture
def run_command():
    return RunCommand()
