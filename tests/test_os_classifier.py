import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest


def _bash_executable():
    if os.name == 'nt':
        git = shutil.which('git')
        assert git, 'Git for Windows is required to test the build scripts.'
        for directory in Path(git).resolve().parents:
            for relative_path in ('bin/bash.exe', 'usr/bin/bash.exe'):
                bash = directory / relative_path
                if bash.is_file():
                    return str(bash)
        raise AssertionError(f'Git Bash was not found alongside {git}')
    bash = shutil.which('bash')
    assert bash, 'Bash is required to test the build scripts.'
    return bash


@pytest.mark.parametrize('git_directory', ['cmd', 'bin', 'mingw64/bin', 'usr/bin'])
def test_windows_shell_selection_uses_git_bash_instead_of_wsl(
    tmp_path, monkeypatch, git_directory
):
    git = tmp_path / 'Git' / git_directory / 'git.exe'
    git_bash = tmp_path / 'Git' / 'bin' / 'bash.exe'
    wsl_bash = tmp_path / 'Windows' / 'System32' / 'bash.exe'
    for executable in (git, git_bash, wsl_bash):
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.touch()
    monkeypatch.setitem(globals(), 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(
        shutil, 'which', lambda command: {'git': str(git), 'bash': str(wsl_bash)}[command]
    )

    assert _bash_executable() == str(git_bash)


@pytest.mark.parametrize(
    ('system', 'architecture', 'returncode', 'output', 'error'),
    [
        ('Darwin', 'x86_64', 1, '', 'Intel Mac builds are not supported'),
        ('Darwin', 'arm64', 0, 'osx-arm64', ''),
        ('MINGW64_NT-10.0', 'x86_64', 0, 'windows-x86_64', ''),
        ('MINGWARM64_NT-10.0', 'ARM64', 0, 'windows-arm64', ''),
        ('MSYS_NT-10.0', 'aarch64', 0, 'windows-arm64', ''),
    ],
)
def test_supported_build_targets(system, architecture, returncode, output, error):
    classifier = Path(__file__).resolve().parents[1] / 'os_classifier.sh'

    result = subprocess.run(
        [
            _bash_executable(), '--noprofile', '--norc', '-c',
            'uname() { case "$1" in -s) echo "$TEST_SYSTEM" ;; '
            '-m) echo "$TEST_ARCH" ;; esac; }; '
            'ACTIONS_RUNNER_ARCH="$TEST_ARCH"; '
            'PROCESSOR_ARCHITECTURE=""; PROCESSOR_ARCHITEW6432=""; source "$1"',
            'classifier-test', classifier.as_posix(),
        ],
        capture_output=True,
        text=True,
        env=os.environ | {
            'TEST_SYSTEM': system,
            'TEST_ARCH': architecture,
        },
        check=False,
    )

    assert result.returncode == returncode, result.stderr or result.stdout
    assert result.stdout.strip() == output
    assert error in result.stderr


def test_windows_host_architecture_takes_priority_over_emulated_shell():
    classifier = Path(__file__).resolve().parents[1] / 'os_classifier.sh'
    result = subprocess.run(
        [
            _bash_executable(), '--noprofile', '--norc', '-c',
            'uname() { case "$1" in -s) echo MSYS_NT-10.0 ;; -m) echo x86_64 ;; esac; }; '
            'ACTIONS_RUNNER_ARCH=""; '
            'PROCESSOR_ARCHITEW6432=ARM64; PROCESSOR_ARCHITECTURE=AMD64; source "$1"',
            'classifier-test', classifier.as_posix(),
        ],
        capture_output=True,
        text=True,
        env=os.environ,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'windows-arm64'


def test_windows_native_python_architecture_overrides_emulated_shell():
    classifier = Path(__file__).resolve().parents[1] / 'os_classifier.sh'
    result = subprocess.run(
        [
            _bash_executable(), '--noprofile', '--norc', '-c',
            'uname() { case "$1" in -s) echo MSYS_NT-10.0 ;; -m) echo x86_64 ;; esac; }; '
            'python() { echo ARM64; }; ACTIONS_RUNNER_ARCH=""; '
            'PROCESSOR_ARCHITEW6432=""; PROCESSOR_ARCHITECTURE=AMD64; source "$1"',
            'classifier-test', classifier.as_posix(),
        ],
        capture_output=True,
        text=True,
        env=os.environ,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'windows-arm64'
