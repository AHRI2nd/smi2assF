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
        bash = Path(git).resolve().parent.parent / 'bin' / 'bash.exe'
        assert bash.is_file(), f'Git Bash was not found at {bash}'
        return str(bash)
    bash = shutil.which('bash')
    assert bash, 'Bash is required to test the build scripts.'
    return bash


def test_windows_shell_selection_uses_git_bash_instead_of_wsl(tmp_path, monkeypatch):
    git = tmp_path / 'Git' / 'cmd' / 'git.exe'
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
    ],
)
def test_supported_build_targets(system, architecture, returncode, output, error):
    classifier = Path(__file__).resolve().parents[1] / 'os_classifier.sh'

    result = subprocess.run(
        [
            _bash_executable(), '--noprofile', '--norc', '-c',
            'uname() { case "$1" in -s) echo "$TEST_SYSTEM" ;; '
            '-m) echo "$TEST_ARCH" ;; esac; }; source "$1"',
            'classifier-test', classifier.as_posix(),
        ],
        capture_output=True,
        text=True,
        env=os.environ | {'TEST_SYSTEM': system, 'TEST_ARCH': architecture},
        check=False,
    )

    assert result.returncode == returncode, result.stderr or result.stdout
    assert result.stdout.strip() == output
    assert error in result.stderr
