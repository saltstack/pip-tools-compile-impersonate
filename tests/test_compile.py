# -*- coding: utf-8 -*-
'''
    test_compile
    ~~~~~~~~~~~~

    Test Static Compilation
'''
# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals
import os
import sys
import shutil

# Import 3rd-party libs
import pytest

PYVER = '{}.{}'.format(*sys.version_info)
TARGET_PLATFORMS = ('linux', 'windows', 'darwin')
REPO_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INPUT_REQUIREMENTS_DIR = os.path.relpath(os.path.join(os.path.dirname(__file__), 'files'), REPO_ROOT)
EXPECTED_REQUIREMENTS_DIR = os.path.relpath(os.path.join(os.path.dirname(__file__), 'files', 'expected'), REPO_ROOT)
TARGET_PYTHON_VERSIONS = ('2.7', '3.4', '3.5', '3.6')

@pytest.mark.parametrize('python_version', TARGET_PYTHON_VERSIONS)
def test_py_version_nested_requirements(run_command, python_version):
    input_requirement = os.path.join(INPUT_REQUIREMENTS_DIR, 'boto3.in')
    compiled_requirements = os.path.join(INPUT_REQUIREMENTS_DIR, 'py{}'.format(python_version), 'boto3.txt')
    expected_requirements = os.path.join(EXPECTED_REQUIREMENTS_DIR, 'py{}'.format(python_version), 'boto3.txt')
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        'pip-tools-compile',
        '-v',
        '--py-version={}'.format(python_version),
        '--platform=linux',
        input_requirement
    )
    assert retcode == 0
    with open(compiled_requirements) as crfh:
        compiled_contents = crfh.read()
    with open(expected_requirements) as erfh:
        expected_contents = erfh.read()
    assert compiled_contents == expected_contents
    if python_version.startswith('2.'):
        assert 'futures' in compiled_contents, \
                'The future library was not found in the compiled output\n{}'.format(compiled_contents)
    else:
        assert 'futures' not in compiled_contents, \
                'The future library was found in the compiled output\n{}'.format(compiled_contents)
