"""
    test_compile
    ~~~~~~~~~~~~

    Test Static Compilation
"""
import logging
import os
import shutil
import sys
import textwrap

import pytest

log = logging.getLogger(__name__)

PYVER = "{}.{}".format(*sys.version_info)
TARGET_PLATFORMS = ("linux", "windows", "darwin")
REPO_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INPUT_REQUIREMENTS_DIR = os.path.relpath(
    os.path.join(os.path.dirname(__file__), "files"), REPO_ROOT
)
EXPECTED_REQUIREMENTS_DIR = os.path.relpath(
    os.path.join(os.path.dirname(__file__), "files", "expected"), REPO_ROOT
)
TARGET_PYTHON_VERSIONS = ("3.5", "3.6", "3.7", "3.8", "3.9", "3.10")


@pytest.mark.parametrize("python_version", TARGET_PYTHON_VERSIONS)
def test_py_version_nested_requirements(run_command, python_version):
    input_requirement = os.path.join(INPUT_REQUIREMENTS_DIR, "boto3.in")
    compiled_requirements = os.path.join(
        INPUT_REQUIREMENTS_DIR, "py{}".format(python_version), "boto3.txt"
    )
    expected_requirements = os.path.join(
        EXPECTED_REQUIREMENTS_DIR, "py{}".format(python_version), "boto3.txt"
    )
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        "pip-tools-compile",
        "-v",
        "--clean-cache",
        "--py-version={}".format(python_version),
        "--platform=linux",
        input_requirement,
    )
    assert retcode == 0
    with open(compiled_requirements) as crfh:
        compiled_contents = crfh.read()
    with open(expected_requirements) as erfh:
        expected_contents = erfh.read()
    assert compiled_contents == expected_contents
    assert (
        "futures" not in compiled_contents
    ), "The future library was found in the compiled output\n{}".format(compiled_contents)


MARKERS_INPUT_REQUIREMENT_TPL = textwrap.dedent(
    """\
    boto3==1.9.121; {marker} == {values[0]}
    boto3==1.9.122; {marker} == {values[1]}
    boto3==1.9.123; {marker} == {values[2]}
    """
)
MARKERS = {
    "os.name": [
        "nt",
        '"posix" and platform_system != "Linux"',
        '"posix" and platform_system != "Darwin"',
    ],
    "sys.platform": [
        "win32",
        "darwin",
        "linux{}".format("2" if sys.version_info.major == 2 else ""),
    ],
    "platform_system": ["Windows", "Darwin", "Linux"],
}


@pytest.mark.parametrize(
    "platform,marker,expected",
    (
        ("windows", "os.name", "boto3==1.9.121"),
        ("darwin", "os.name", "boto3==1.9.122"),
        ("linux", "os.name", "boto3==1.9.123"),
        ("windows", "sys.platform", "boto3==1.9.121"),
        ("darwin", "sys.platform", "boto3==1.9.122"),
        ("linux", "sys.platform", "boto3==1.9.123"),
        ("windows", "platform_system", "boto3==1.9.121"),
        ("darwin", "platform_system", "boto3==1.9.122"),
        ("linux", "platform_system", "boto3==1.9.123"),
    ),
)
def test_markers(run_command, platform, marker, expected):
    input_requirement_name = "boto3-markers"
    input_requirement = os.path.join(INPUT_REQUIREMENTS_DIR, "{}.in".format(input_requirement_name))
    with open(input_requirement, "w") as wfh:
        wfh.write(
            MARKERS_INPUT_REQUIREMENT_TPL.format(
                marker=marker,
                values=[
                    value if value.startswith('"') else '"{}"'.format(value)
                    for value in MARKERS[marker]
                ],
            )
        )
    log.info("Input Requirements:\n---------\n%s\n---------", open(input_requirement).read())
    compiled_requirements = os.path.join(
        INPUT_REQUIREMENTS_DIR,
        "py{}.{}".format(*sys.version_info),
        "{}.txt".format(input_requirement_name),
    )
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        "pip-tools-compile",
        "-v",
        "--clean-cache",
        "--platform={}".format(platform),
        input_requirement,
    )
    assert retcode == 0
    with open(compiled_requirements) as crfh:
        compiled_contents = crfh.read()
    assert (
        expected in compiled_contents
    ), "The {!r} was not found in the compiled output\n{}".format(expected, compiled_contents)


@pytest.mark.parametrize("version", [225, 300])
@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
@pytest.mark.parametrize("python_version", TARGET_PYTHON_VERSIONS)
def test_pywin32(run_command, platform, version, python_version):
    """
    pywin32 has been an issue when mocking the requirements file compilation. test it.
    """
    version_info = tuple(int(part) for part in python_version.split("."))
    if version_info >= (3, 10):
        # There's no wheel package for Py3.10+
        pytest.skip("There's no pywin32=={} wheel package for Py3.10+".format(version))
    input_requirement_name = "pywin32-req"
    input_requirement = os.path.join(INPUT_REQUIREMENTS_DIR, "{}.in".format(input_requirement_name))
    with open(input_requirement, "w") as wfh:
        wfh.write(
            textwrap.dedent(
                """\
            pep8
            pywin32=={}; sys.platform == 'win32'
            """.format(
                    version
                )
            )
        )
    compiled_requirements = os.path.join(
        INPUT_REQUIREMENTS_DIR,
        "py{}".format(python_version),
        "{}.txt".format(input_requirement_name),
    )
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        "pip-tools-compile",
        "-v",
        "--clean-cache",
        "--platform={}".format(platform),
        "--py-version={}".format(python_version),
        "-vv",
        input_requirement,
    )
    assert retcode == 0
    with open(compiled_requirements) as crfh:
        compiled_contents = crfh.read()
    if platform == "windows":
        assert (
            "pywin32=={}".format(version) in compiled_contents
        ), "The pywin32 requirement was not found in the compiled output\n{}".format(
            compiled_contents
        )
    else:
        assert (
            "pywin32=={}".format(version) not in compiled_contents
        ), "The pywin32 requirement was found in the compiled output\n{}".format(compiled_contents)


@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
def test_jsonschema(run_command, platform):
    """
    jsonschema pulls in backports under py2, make sure that under py3 those don't end up in the final requirements
    """
    input_requirement_name = "jsonschema==2.6.0"
    input_requirement = os.path.join(INPUT_REQUIREMENTS_DIR, "{}.in".format(input_requirement_name))
    with open(input_requirement, "w") as wfh:
        wfh.write(input_requirement_name + "\n")
    compiled_requirements = os.path.join(
        INPUT_REQUIREMENTS_DIR, "py3.5", "{}.txt".format(input_requirement_name)
    )
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        "pip-tools-compile",
        "-v",
        "--clean-cache",
        "--py-version=3.5",
        "--platform={}".format(platform),
        input_requirement,
    )
    assert retcode == 0
    with open(compiled_requirements) as crfh:
        compiled_contents = crfh.read()

    assert "functools" not in compiled_contents


@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
@pytest.mark.parametrize("python_version", TARGET_PYTHON_VERSIONS)
@pytest.mark.skip("Salt no longer pins pyobjc. Skipping this test for now")
def test_pyobjc(run_command, platform, python_version):
    """
    pyobjc has been an issue when mocking the requirements file compilation. test it.
    """
    version_info = tuple(int(part) for part in python_version.split("."))
    if version_info < (3, 6):
        # There's no wheel package for Py3.5
        pytest.skip("There's no pyobjc-core==6.2 wheel package for Py3.5")
    input_requirement_name = "pyobjc-req"
    input_requirement = os.path.join(INPUT_REQUIREMENTS_DIR, "{}.in".format(input_requirement_name))
    with open(input_requirement, "w") as wfh:
        wfh.write(
            textwrap.dedent(
                """\
            pep8
            pyobjc==6.2; sys.platform == 'darwin'
            """
            )
        )
    compiled_requirements = os.path.join(
        INPUT_REQUIREMENTS_DIR,
        "py{}".format(python_version),
        "{}.txt".format(input_requirement_name),
    )
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        "pip-tools-compile",
        "-v",
        "--clean-cache",
        "--platform={}".format(platform),
        "--py-version={}".format(python_version),
        input_requirement,
    )
    assert retcode == 0
    with open(compiled_requirements) as crfh:
        compiled_contents = crfh.read()
    if platform == "darwin":
        assert (
            "pyobjc==" in compiled_contents
        ), "The pyobjc requirement was not found in the compiled output\n{}".format(
            compiled_contents
        )
    else:
        assert (
            "pyobjc==" not in compiled_contents
        ), "The pyobjc requirement was found in the compiled output\n{}".format(compiled_contents)


@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
@pytest.mark.parametrize("python_version", TARGET_PYTHON_VERSIONS)
def test_backports_ssl_match_hostname(run_command, platform, python_version):
    """
    pywin32 has been an issue when mocking the requirements file compilation. test it.
    """
    version_info = tuple(int(part) for part in python_version.split("."))
    input_requirement_name = "backports-ssl-match-hostname"
    input_requirement = os.path.join(INPUT_REQUIREMENTS_DIR, "{}.in".format(input_requirement_name))
    with open(input_requirement, "w") as wfh:
        wfh.write(
            textwrap.dedent(
                """\
            pep8
            backports.ssl-match-hostname==3.7.0.1 ; python_version < "3.7"
            """
            )
        )
    compiled_requirements = os.path.join(
        INPUT_REQUIREMENTS_DIR,
        "py{}".format(python_version),
        "{}.txt".format(input_requirement_name),
    )
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        "pip-tools-compile",
        "-v",
        "--clean-cache",
        "--platform={}".format(platform),
        "--py-version={}".format(python_version),
        "-vv",
        input_requirement,
    )
    assert retcode == 0
    with open(compiled_requirements) as crfh:
        compiled_contents = crfh.read()
    if version_info < (3, 7):
        assert "backports.ssl-match-hostname" in compiled_contents
    else:
        assert "backports.ssl-match-hostname" not in compiled_contents


def test_boto3_py35(run_command):
    """
    There's not boto3==1.17.66 for Py3.5
    """
    input_requirement_name = "boto3-py35"
    input_requirement = os.path.join(INPUT_REQUIREMENTS_DIR, "{}.in".format(input_requirement_name))
    with open(input_requirement, "w") as wfh:
        wfh.write(
            textwrap.dedent(
                """\
            pep8
            boto3>=1.17.66
            """
            )
        )
    compiled_requirements = os.path.join(
        INPUT_REQUIREMENTS_DIR,
        "py3.5",
        "{}.txt".format(input_requirement_name),
    )
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        "pip-tools-compile",
        "-v",
        "--clean-cache",
        "--platform=linux",
        "--py-version=3.5",
        "-vv",
        input_requirement,
    )
    # It should fail
    assert retcode == 1

    compiled_requirements = os.path.join(
        INPUT_REQUIREMENTS_DIR,
        "py3.6",
        "{}.txt".format(input_requirement_name),
    )
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        "pip-tools-compile",
        "-v",
        "--clean-cache",
        "--platform=linux",
        "--py-version=3.6",
        "-vv",
        input_requirement,
    )
    # It should NOT fail
    assert retcode == 0


@pytest.mark.parametrize("platform", ["linux", "darwin", "windows"])
@pytest.mark.parametrize("python_version", TARGET_PYTHON_VERSIONS)
def test_pygit2(run_command, platform, python_version):
    """
    Test pygit2
    """
    input_requirement_name = "pygit2"
    input_requirement = os.path.join(INPUT_REQUIREMENTS_DIR, "{}.in".format(input_requirement_name))
    with open(input_requirement, "w") as wfh:
        wfh.write(
            textwrap.dedent(
                """\
            pygit2>=1.5.0
            """
            )
        )
    compiled_requirements = os.path.join(
        INPUT_REQUIREMENTS_DIR,
        "py{}".format(python_version),
        "{}.txt".format(input_requirement_name),
    )
    if os.path.exists(compiled_requirements):
        os.unlink(compiled_requirements)
    # Run it through pip-tools-compile
    retcode = run_command(
        "pip-tools-compile",
        "-v",
        "--clean-cache",
        "--platform={}".format(platform),
        "--py-version={}".format(python_version),
        "-vv",
        input_requirement,
    )
    assert retcode == 0
    with open(compiled_requirements) as crfh:
        compiled_contents = crfh.read()
    assert "pygit2" in compiled_contents
