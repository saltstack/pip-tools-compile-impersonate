# Pre-Commit pip-tools-compile-impersonate

This is a [pre-commit](http://pre-commit.com/) hook which is a simple wrapper
around [pip-tools](https://github.com/jazzband/pip-tools) `pip-compile` CLI
script which provides functionality to impersonate platforms.

The script is currently tailored to run under linux and can impersonate Windows.

## Example Usage

```yaml
repos:
  - repo: https://github.com/saltstack/pip-tools-compile-impersonate
    rev: master
    hooks:
      - id: pip-tools-compile
        alias: compile-linux-py3-zmq-requirements
        name: Linux Py3 ZeroMQ Requirements
        files: ^requirements/static/(.*)\.in$
        exclude: ^requirements/static/windows\.in$
        args:
          - --out-prefix=zeromq
          - --include=requirements/zeromq.txt
          - --include=requirements/pytest.txt
        language_version: python3
      - id: pip-tools-compile
        alias: compile-linux-py2-zmq-requirements
        name: Linux Py2 ZeroMQ Requirements
        files: ^requirements/static/(.*)\.in$
        exclude: ^requirements/static/windows\.in$
        args:
          - --out-prefix=zeromq
          - --include=requirements/zeromq.txt
          - --include=requirements/pytest.txt
        language_version: python2
      - id: pip-tools-compile
        alias: compile-linux-py3-raet-requirements
        name: Linux Py3 RAET Requirements
        files: ^requirements/static/(.*)\.in$
        exclude: ^requirements/static/windows\.in$
        args:
          - --out-prefix=raet
          - --include=requirements/raet.txt
          - --include=requirements/pytest.txt
        language_version: python3
      - id: pip-tools-compile
        alias: compile-linux-py2-raet-requirements
        name: Linux Py2 RAET Requirements
        files: ^requirements/static/(.*)\.in$
        exclude: ^requirements/static/windows\.in$
        args:
          - --out-prefix=raet
          - --include=requirements/raet.txt
          - --include=requirements/pytest.txt
        language_version: python2
      - id: pip-tools-compile
        alias: compile-windows-py3-zmq-requirements
        name: Windows Py3 ZeroMQ Requirements
        files: ^requirements/static/windows\.in$
        args:
          - --platform=windows
          - --out-prefix=zeromq
          - --include=requirements/zeromq.txt
          - --include=requirements/pytest.txt
        language_version: python3
      - id: pip-tools-compile
        alias: compile-windows-py2-zmq-requirements
        name: Windows Py2 ZeroMQ Requirements
        files: ^requirements/static/windows\.in$
        args:
          - --platform=windows
          - --out-prefix=zeromq
          - --include=requirements/zeromq.txt
          - --include=requirements/pytest.txt
        language_version: python2
      - id: pip-tools-compile
        alias: compile-windows-py3-raet-requirements
        name: Windows Py3 RAET Requirements
        files: ^requirements/static/windows\.in$
        args:
          - --out-prefix=raet
          - --platform=windows
          - --include=requirements/raet.txt
          - --include=requirements/pytest.txt
          - --rebuild
        language_version: python3
      - id: pip-tools-compile
        alias: compile-windows-py2-raet-requirements
        name: Windows Py2 RAET Requirements
        files: ^requirements/static/windows\.in$
        args:
          - --out-prefix=raet
          - --platform=windows
          - --include=requirements/raet.txt
          - --include=requirements/pytest.txt
        language_version: python2
```
