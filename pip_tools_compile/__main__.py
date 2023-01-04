"""
pip-tools-compile
~~~~~~~~~~~~~~~~~

Wrapper around pip-tools to "impersonate" different distributions when compiling requirements
"""
import argparse
import atexit
import functools
import io
import logging
import os
import platform
import re
import shutil
import sys
import textwrap
import traceback
from collections import namedtuple
from unittest import mock

from pip_tools_compile import __version__

SYSTEM = platform.system().lower()
CAPTURE_OUTPUT = os.environ.get("CAPTURE_OUTPUT", "1") == "1"
VERBOSE_COMPILE = os.environ.get("VERBOSE_COMPILE", "0") == "1"

LOG_STREAM = io.StringIO()
logging.basicConfig(
    level=logging.DEBUG,
    stream=LOG_STREAM,
    datefmt="%H:%M:%S",
    format="%(asctime)s,%(msecs)03.0f [%(name)-5s:%(lineno)-4d][%(levelname)-8s] %(message)s",
)

# Keep a reference to the original DependencyCache class
from piptools.cache import DependencyCache
from piptools.repositories import PyPIRepository as _PyPIRepository
from pip._internal.models.target_python import TargetPython as _TargetPython
from pip._vendor.packaging.markers import default_environment

DEFAULT_ENVIRONMENT = default_environment()


class PyPIRepository(_PyPIRepository):
    def __init__(self, mocked_python_version, mocked_platform, pip_args, cache_dir):
        pip_args = list(pip_args)
        pip_args.append("--python-version={}.{}".format(*mocked_python_version))
        pip_args.append("--platform={}".format(mocked_platform))
        super().__init__(pip_args, cache_dir)
        # We re-initialize self.finder because we want to pass the target_python
        # which avoids a lot of sys,version_info patching
        self.finder = self.command._build_package_finder(
            options=self.options,
            session=self.session,
            target_python=TargetPython(mocked_python_version, mocked_platform),
        )
        self._mocked_python_version = mocked_python_version
        self._mocked_platform = mocked_platform
        # piptools does not pass py_version_info when creating the resolver.
        # Let's force it to do that
        self._original_make_resolver = self.command.make_resolver
        self.command.make_resolver = self._make_resolver

    def _make_resolver(self, *args, py_version_info=None, **kwargs):
        if py_version_info is None:
            py_version_info = self._mocked_python_version
        return self._original_make_resolver(*args, py_version_info=py_version_info, **kwargs)


class TargetPython(_TargetPython):
    def __init__(
        self,
        mocked_python_version,
        mocked_platform,
        platforms=None,
        py_version_info=None,
        abis=None,
        implementation=None,
    ):
        if py_version_info is None:
            py_version_info = mocked_python_version
        if platforms is None:
            platforms = [mocked_platform]
        super().__init__(
            platforms=platforms,
            py_version_info=py_version_info,
            abis=abis,
            implementation=implementation,
        )


real_version_info = sys.version_info


log = logging.getLogger("pip-tools-compile")

version_info = namedtuple("version_info", ["major", "minor", "micro", "releaselevel", "serial"])


class ImpersonateSystem:

    __slots__ = ("_python_version_info", "_platform", "platform_machine")

    def __init__(self, python_version_info, platform, machine=None):
        parts = [int(part) for part in python_version_info.split(".") if part.isdigit()]
        python_version_info = list(sys.version_info)
        for idx, part in enumerate(parts):
            python_version_info[idx] = part
        python_version_info = version_info(*python_version_info)
        self._python_version_info = python_version_info
        if platform == "windows":
            platform = "win32"
        if platform == "freebsd":
            platform = "freebsd14"
        self._platform = platform
        if machine is not None:
            assert machine.lower() in ("arm64", "amd64", "x86_64")
            self.platform_machine = machine

    def get_mocks(self):
        yield mock.patch(
            "piptools.scripts.compile.DependencyCache",
            wraps=functools.partial(
                tweak_piptools_depcache_filename, self._python_version_info, self._platform
            ),
        )
        yield mock.patch(
            "piptools.scripts.compile.PyPIRepository",
            wraps=functools.partial(PyPIRepository, self._python_version_info, self._platform),
        )
        yield mock.patch(
            "pip._vendor.packaging.markers.default_environment",
            wraps=functools.partial(tweak_packaging_markers, self),
        )
        yield mock.patch(
            "pip._vendor.distlib.markers.DEFAULT_CONTEXT",
            new_callable=mock.PropertyMock(return_value=tweak_packaging_markers(self)),
        )

    def __enter__(self):
        for mock_obj in self.get_mocks():
            if mock_obj is None:
                continue
            mock_obj.start()
        return self

    def __exit__(self, *_):
        mock.patch.stopall()


def tweak_piptools_depcache_filename(version_info, platform, *args, **kwargs):
    depcache = DependencyCache(*args, **kwargs)
    # pylint: disable=protected-access
    if os.environ.get("USE_STATIC_REQUIREMENTS", "0") == "1":
        use_static_requirements = "-static"
    else:
        use_static_requirements = ""
    cache_file = os.path.join(
        os.path.dirname(depcache._cache_file),
        "depcache{}-{}-ptc{}-py{}.{}-mocked-py{}.{}.json".format(
            use_static_requirements,
            platform,
            __version__,
            *sys.version_info[:2],
            *version_info[:2],
        ),
    )
    log.info("Tweaking the pip-tools depcache file to: %s", cache_file)
    depcache._cache_file = cache_file
    # pylint: enable=protected-access
    if os.environ["PIP_TOOLS_COMPILE_CLEAN_CACHE"] == "1":
        if os.path.exists(cache_file):
            os.unlink(cache_file)
    return depcache


def tweak_packaging_markers(impersonation):
    environment = DEFAULT_ENVIRONMENT.copy()
    environment["os_name"] = impersonation.os_name
    environment["platform_machine"] = impersonation.platform_machine
    environment["platform_release"] = impersonation.platform_release
    environment["platform_system"] = impersonation.platform_system
    environment["platform_version"] = impersonation.platform_version
    environment["python_version"] = "{}.{}".format(*impersonation._python_version_info)
    environment["python_full_version"] = "{}.{}.{}".format(*impersonation._python_version_info)
    environment["implementation_version"] = environment["python_full_version"]
    environment["sys_platform"] = impersonation._platform
    return environment


class ImpersonateWindows(ImpersonateSystem):
    os_name = "nt"
    platform_machine = "AMD64"
    platform_release = "8.1"
    platform_system = "Windows"
    platform_version = "6.3.9600"

    def get_mocks(self):
        yield from super().get_mocks()
        if SYSTEM != "windows":
            # We don't want pip trying query python's internals, it knows how to mock that internal information
            yield mock.patch("pip._vendor.packaging.tags._get_config_var", return_value=None)
            yield mock.patch("pip._internal.network.session.libc_ver", return_value=("", ""))
            yield mock.patch(
                "pip._vendor.packaging.tags._platform_tags", return_value=["win_amd64"]
            )


class ImpersonateDarwin(ImpersonateSystem):
    os_name = "posix"
    platform_machine = "x86_64"
    platform_release = "19.2.0"
    platform_system = "Darwin"
    platform_version = "Darwin Kernel Version 19.2.0: Sat Nov  9 03:47:04 PST 2019; root:xnu-6153.61.1~20/RELEASE_X86_64"

    def get_mocks(self):
        yield from super().get_mocks()
        if SYSTEM != "darwin":
            # We don't want pip trying query python's internals, it knows how to mock that internal information
            yield mock.patch("pip._vendor.packaging.tags._get_config_var", return_value=None)
            tags = []
            for version in range(4, 16):
                for cpu in ("fat32", "fat64", "intel", "universal", "x86_64"):
                    tags.append("macosx_10_{}_{}".format(version, cpu))
            yield mock.patch("pip._vendor.packaging.tags._platform_tags", return_value=tags)


class ImpersonateLinux(ImpersonateSystem):
    os_name = "posix"
    platform_machine = "x86_64"
    platform_release = "4.19.29-1-lts"
    platform_system = "Linux"
    platform_version = "#1 SMP Thu Mar 14 15:39:08 CET 2019"

    def get_mocks(self):
        yield from super().get_mocks()
        if SYSTEM != "linux":
            # We don't want pip trying query python's internals, it knows how to mock that internal information
            yield mock.patch("pip._vendor.packaging.tags._get_config_var", return_value=None)
            yield mock.patch(
                "pip._vendor.packaging.tags._platform_tags",
                return_value=[
                    "linux_x86_64",
                    "manylinux1_x86_64",
                    "manylinux2010_x86_64",
                    "manylinux2014_x86_64",
                ],
            )


class ImpersonateFreeBSD(ImpersonateSystem):
    os_name = "posix"
    platform_machine = "x86_64"
    platform_release = "14.0-CURRENT"
    platform_system = "FreeBSD"
    platform_version = (
        "FreeBSD 14.0-CURRENT #35 main-n246214-78ffcb86d98: Tue Apr 20 10:59:32 CEST 2021     "
        "root@krion.cc:/usr/obj/usr/src/amd64.amd64/sys/GENERIC"
    )

    def get_mocks(self):
        yield from super().get_mocks()
        if SYSTEM != "freebsd":
            # We don't want pip trying query python's internals, it knows how to mock that internal information
            yield mock.patch("pip._vendor.packaging.tags._get_config_var", return_value=None)
            yield mock.patch(
                "pip._vendor.packaging.tags._platform_tags",
                return_value=[
                    "{}_{}_{}".format(
                        self.platform_system.lower(),
                        self.platform_release.replace("-", "_").replace(".", "_"),
                        self.platform_machine,
                    )
                ],
            )


class CatureSTDs:
    def __init__(self):
        self._stdout = io.StringIO()
        self._stderr = io.StringIO()
        self._sys_stdout = sys.stdout
        self._sys_stderr = sys.stderr

    def __enter__(self):
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        return self

    def __exit__(self, *args):
        sys.stdout = self._sys_stdout
        sys.stderr = self._sys_stderr
        if not CAPTURE_OUTPUT:
            self._stdout.seek(0)
            sys.stdout.write(self._stdout.read())
            self._stderr.seek(0)
            sys.stderr.write(self._stderr.read())

    @property
    def stdout(self):
        pos = self._stdout.tell()
        self._stdout.seek(0)
        try:
            return self._stdout.read()
        finally:
            self._stdout.seek(pos)

    @property
    def stderr(self):
        pos = self._stderr.tell()
        self._stderr.seek(0)
        try:
            return self._stderr.read()
        finally:
            self._stderr.seek(pos)


def compile_requirement_file(source, dest, options, unknown_args):
    log.info("Compiling requirements to %s", dest)

    input_rewrites = {}
    passthrough_lines = {}

    regexes = []
    for regex in options.passthrough_line_from_input:
        regexes.append(re.compile(regex))

    call_args = ["pip-compile", "-o", dest]
    if unknown_args:
        for unknown_arg in unknown_args:
            if "{py_version}" in unknown_arg:
                unknown_arg = unknown_arg.format(py_version=options.py_version)
            call_args.append(unknown_arg)
    if options.include:
        includes = []
        for input_file in options.include:
            out_contents = []
            input_file = input_file.format(py_version=options.py_version)
            with open(input_file) as rfh:
                in_contents = rfh.read()
            for line in in_contents.splitlines():
                constraint_flag = req_path = None
                if line.strip().startswith("-c "):
                    constraint_flag = "-c "
                    req_path = os.path.abspath(
                        line.split()[-1].format(
                            py_version=options.py_version, platform=options.platform
                        )
                    )
                if line.strip().startswith("--constraint="):
                    constraint_flag = "--constraint="
                    req_path = os.path.abspath(
                        line.split("--constraint=")[-1].format(
                            py_version=options.py_version, platform=options.platform
                        )
                    )
                if constraint_flag and req_path:
                    line = f"{constraint_flag}{os.path.relpath(req_path, os.getcwd())}"
                    if input_file not in input_rewrites:
                        input_rewrites[input_file] = input_file
                        shutil.move(input_file, input_file + ".bak")
                        atexit.register(shutil.move, input_file + ".bak", input_file)
                match_found = False
                for regex in regexes:
                    if match_found:
                        break
                    if regex.match(line):
                        match_found = True
                        if input_file not in input_rewrites:
                            input_rewrites[input_file] = input_file
                            shutil.move(input_file, input_file + ".bak")
                            atexit.register(shutil.move, input_file + ".bak", input_file)
                        if input_file not in passthrough_lines:
                            passthrough_lines[input_file] = []
                if match_found:
                    passthrough_lines[input_file].append(line)
                    # Skip this line
                    continue
                out_contents.append(line)
            if input_file in input_rewrites:
                with open(input_rewrites[input_file], "w") as wfh:
                    for line in out_contents:
                        wfh.write("{}\n".format(line))
                includes.append(input_rewrites[input_file])
            else:
                includes.append(input_file)
        call_args += includes

    with open(source) as rfh:
        source_contents = rfh.read()
    if "{py_version}" in source_contents:
        out_contents = []
        for line in source_contents.splitlines():
            constraint_flag = req_path = None
            if line.strip().startswith("-c "):
                constraint_flag = "-c "
                req_path = os.path.abspath(
                    line.split()[-1].format(
                        py_version=options.py_version, platform=options.platform
                    )
                )
            if line.strip().startswith("--constraint="):
                constraint_flag = "--constraint="
                req_path = os.path.abspath(
                    line.split("--constraint=")[-1].format(
                        py_version=options.py_version, platform=options.platform
                    )
                )
            if constraint_flag and req_path:
                line = f"{constraint_flag}{os.path.relpath(req_path, os.getcwd())}"
                if os.path.exists(source):
                    shutil.move(source, source + ".bak")
                    atexit.register(shutil.move, source + ".bak", source)
            out_contents.append(line)
        with open(source, "w") as wfh:
            for line in out_contents:
                wfh.write("{}\n".format(line))
    call_args.append(source)

    original_sys_arg = sys.argv[:]
    success = False
    try:
        print("Running: {}".format(" ".join(call_args)))
        if options.machine:
            print("  Impersonating CPU: {}".format(options.machine))
        print("  Impersonating: {}".format(options.platform))
        print("  Mocked Python Version: {}".format(options.py_version))
        sys.argv = call_args[:]
        log.debug("Switching sys.argv to: %s", sys.argv)
        try:
            import piptools.scripts.compile

            piptools.scripts.compile.cli()
        except SystemExit as exc:
            success = exc.code == 0
            if success is False:
                print("Failed to compile requirements. Exit code: {}".format(exc.code))
        except Exception:  # pylint: disable=broad-except
            success = False
            print("Exception raised when processing {}".format(source))
            print(traceback.format_exc())
    finally:
        if success is True:
            log.info("Finished compiling %s", dest)

            if input_rewrites:
                with open(dest) as rfh:
                    dest_contents = rfh.read()

                for input_file, rewriten_file in input_rewrites.items():
                    if rewriten_file in dest_contents:
                        dest_contents = dest_contents.replace(rewriten_file, input_file)

                    try:
                        os.unlink(rewriten_file)
                    except OSError:
                        pass

                with open(dest, "w") as wfh:
                    wfh.write(dest_contents)
                    for input_file, lines in passthrough_lines.items():
                        wfh.write("# Passthrough dependencies from {}\n".format(input_file))
                        for line in lines:
                            wfh.write("{}\n".format(line))

        sys.argv = original_sys_arg

    # Flag success
    return success


def show_info_to_patch():
    print("Generating information under {}\n".format(platform.system()))
    print(" * pip._vendor.packaging.markers.default_environment() output:")
    for key in sorted(DEFAULT_ENVIRONMENT):
        print("  * {}: '{}'".format(key, DEFAULT_ENVIRONMENT[key]))
    import pip._vendor.packaging.tags

    print(" * pip._vendor.packaging.tags._platform_tags:")
    for tag in sorted(pip._vendor.packaging.tags._platform_tags()):
        print("  * '{}'".format(tag))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--show-info-to-patch",
        action="store_true",
        help="Print out the information we require to patch the multiple platforms",
    )
    parser.add_argument(
        "--platform",
        choices=("windows", "darwin", "linux", "freebsd"),
        default=platform.system().lower(),
    )
    parser.add_argument(
        "--machine",
        choices=("amd64", "arm64", "x86_64"),
        default=None,
    )
    parser.add_argument(
        "--static-requirements",
        action="store_true",
        default=False,
        help="Set USE_STATIC_REQUIREMENTS=1 environment variable prior to compiling requirements",
    )
    parser.add_argument("--py-version", default="{}.{}".format(*sys.version_info))
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--out-prefix", default=None)
    parser.add_argument(
        "--remove-line",
        default=[],
        action="append",
        help="Python regular experession to search and remove from the compiled requirements and remove it",
    )
    parser.add_argument(
        "--passthrough-line-from-input",
        default=[],
        action="append",
        help=(
            "Python regular expression to search and remove from the input requirements"
            "and append in the destination requirements file"
        ),
    )
    parser.add_argument(
        "--clean-cache",
        action="store_true",
        default=False,
        help="Clean pip-tools dependency cache files",
    )
    parser.add_argument("files", nargs="*")

    options, unknown_args = parser.parse_known_args()

    if options.show_info_to_patch:
        show_info_to_patch()
        parser.exit(0)

    if not options.files:
        parser.exit(2, "Please pass at least one requirement file")

    os.environ["USE_STATIC_REQUIREMENTS"] = "1" if options.static_requirements else "0"

    os.environ["PIP_TOOLS_COMPILE_CLEAN_CACHE"] = "1" if options.clean_cache else "0"

    if SYSTEM == "windows":
        print(
            "\n"
            "===================================================================================================\n"
            "  Windows Preliminary Support. Please Run In A Linux Docker Container Instead In Case Of Problems  \n"
            "===================================================================================================\n"
            "\n",
            file=sys.stderr,
        )

    if SYSTEM == "darwin":
        print(
            "\n"
            "=================================================================================================\n"
            "  macOS Preliminary Support. Please Run In A Linux Docker Container Instead In Case Of Problems  \n"
            "=================================================================================================\n"
            "\n",
            file=sys.stderr,
        )

    if sys.version_info >= (3, 10):
        print(
            "\n"
            "=============================================================================\n"
            "  Py3.10+ Preliminary Support. Please Run Under Py<3.10 In Case Of Problems  \n"
            "=============================================================================\n"
            "\n",
            file=sys.stderr,
        )

    impersonations = {
        "darwin": ImpersonateDarwin,
        "windows": ImpersonateWindows,
        "linux": ImpersonateLinux,
        "freebsd": ImpersonateFreeBSD,
    }

    regexes = []
    for regex in options.remove_line:
        regexes.append(re.compile(regex))

    stdout = stderr = None
    exitcode = 0

    with CatureSTDs() as capstds:
        with impersonations[options.platform](
            options.py_version, options.platform, options.machine
        ):
            import piptools.scripts.compile

            for fpath in options.files:
                if not fpath.endswith(".in"):
                    continue

                # Return the log strem to 0, either to write a log file in case of an error,
                # or to overwrite the contents for this next fpath
                LOG_STREAM.seek(0)

                source_dir = os.path.dirname(fpath)
                if options.output_dir:
                    dest_dir = options.output_dir
                else:
                    dest_dir = os.path.join(source_dir, "py{}".format(options.py_version))
                if not os.path.isdir(dest_dir):
                    os.makedirs(dest_dir)
                outfile = os.path.basename(fpath).replace(".in", ".txt")
                if options.out_prefix:
                    outfile = "{}-{}".format(options.out_prefix, outfile)
                outfile_path = os.path.join(dest_dir, outfile)
                if not compile_requirement_file(fpath, outfile_path, options, unknown_args):
                    exitcode = 1
                    error_logfile = outfile_path.replace(".txt", ".log")
                    with open(error_logfile, "w") as wfh:
                        LOG_STREAM.seek(0)
                        wfh.write(
                            ">>>>>>> LOGS >>>>>>>>>\n{}\n<<<<<<< LOGS <<<<<<<<<\n".format(
                                LOG_STREAM.read().strip()
                            )
                        )
                        wfh.write(
                            "\n>>>>>>> STDOUT >>>>>>>\n{}\n<<<<<<< STDOUT <<<<<<<\n".format(
                                capstds.stdout.strip()
                            )
                        )
                        wfh.write(
                            "\n>>>>>>> STDERR >>>>>>>\n{}\n<<<<<<< STDERR <<<<<<<\n".format(
                                capstds.stderr.strip()
                            )
                        )
                        print("Error log file at {}".format(error_logfile))
                    continue

                if SYSTEM == "windows":
                    with open(outfile_path) as rfh:
                        contents = re.sub(
                            "'([^']*)'", r"\1", rfh.read().replace("\\", "/"), re.MULTILINE
                        )
                    with open(outfile_path, "w") as wfh:
                        wfh.write(contents)

                if not regexes:
                    continue

                with open(outfile_path) as rfh:
                    in_contents = rfh.read()

                out_contents = []
                for line in in_contents.splitlines():
                    print("Processing line: {!r} // {}".format(line, [r.pattern for r in regexes]))
                    for regex in regexes:
                        if regex.match(line):
                            print(
                                "Line commented out by regex '{}': '{}'".format(regex.pattern, line)
                            )
                            line = textwrap.dedent(
                                """\
                                # Next line explicitly commented out by {} because of the following regex: '{}'
                                # {}""".format(
                                    os.path.basename(__file__), regex.pattern, line
                                )
                            )
                            break
                    out_contents.append(line)

                out_contents = os.linesep.join(out_contents) + os.linesep
                with open(outfile_path, "w") as wfh:
                    wfh.write(out_contents)

            if exitcode:
                stdout = capstds.stdout
                stderr = capstds.stderr

    if stdout:
        sys.__stdout__.write(capstds.stdout)
    if stderr:
        sys.__stderr__.write(capstds.stderr)
    sys.exit(exitcode)


if __name__ == "__main__":
    main()
