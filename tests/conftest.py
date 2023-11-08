"""
conftest
~~~~~~~~
"""
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

import pytest

REPO_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

log = logging.getLogger(__name__)


@dataclass(frozen=True)
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

    exitcode: int
    stdout: str
    stderr: str
    cmdline: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.exitcode, int):
            raise ValueError(f"'exitcode' needs to be an integer, not '{type(self.exitcode)}'")

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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
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
