"""
conftest
~~~~~~~~
"""
import logging
import os
import subprocess
import sys
from collections import namedtuple

import attr
import pytest

REPO_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class ProcessResult:
    """
    This class holds the resulting data from a subprocess command.

    :keyword int exitcode:
        The exitcode returned by the process
    :keyword str stdout:
        The ``stdout`` returned by the process
    :keyword str stderr:
        The ``stderr`` returned by the process
    :keyword list,tuple cmdline:
        The command line used to start the process

    .. admonition:: Note

        Cast :py:class:`~ProcessResult` to a string to pretty-print it.
    """

    exitcode = attr.ib()
    stdout = attr.ib()
    stderr = attr.ib()
    cmdline = attr.ib(default=None, kw_only=True)

    @exitcode.validator
    def _validate_exitcode(self, attribute, value):
        if not isinstance(value, int):
            raise ValueError(f"'exitcode' needs to be an integer, not '{type(value)}'")

    def __str__(self):
        """
        Pretty print the class instance.
        """
        message = self.__class__.__name__
        if self.cmdline:
            message += f"\n Command Line: {self.cmdline}"
        if self.exitcode is not None:
            message += f"\n Exitcode: {self.exitcode}"
        if self.stdout or self.stderr:
            message += "\n Process Output:"
        if self.stdout:
            message += f"\n   >>>>> STDOUT >>>>>\n{self.stdout}\n   <<<<< STDOUT <<<<<"
        if self.stderr:
            message += f"\n   >>>>> STDERR >>>>>\n{self.stderr}\n   <<<<< STDERR <<<<<"
        return message + "\n"


class RunCommand:
    def __init__(self):
        self.argv = []
        self.environ = os.environ.copy()
        self.environ["CAPTURE_OUTPUT"] = "1"

    def __call__(self, *args):
        cmdline = self.argv + list(args)
        log.info("Running: %r", " ".join(cmdline))
        proc = subprocess.run(
            cmdline,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=self.environ,
        )
        ret = ProcessResult(
            proc.returncode, proc.stdout.rstrip(), proc.stderr.rstrip(), cmdline=proc.args
        )
        log.debug(ret)
        return ret.exitcode


@pytest.fixture
def run_command():
    return RunCommand()
