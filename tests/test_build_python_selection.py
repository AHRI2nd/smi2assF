"""Execute build preflight against controlled interpreter version reports."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def build_preflight(tmp_path, versions, requested, *, report_crlf=False):
    shutil.copy(ROOT / 'build.sh', tmp_path / 'build.sh')
    helper = ROOT / 'scripts/python_runtime.sh'
    if helper.exists():
        (tmp_path / 'scripts').mkdir()
        shutil.copy(helper, tmp_path / 'scripts/python_runtime.sh')
    classifier = tmp_path / 'os_classifier.sh'
    classifier.write_text('#!/usr/bin/env bash\necho windows-x86_64\n')
    classifier.chmod(0o755)
    for folder, actual in versions.items():
        executable = tmp_path / ('build/venv-py' + folder + '/bin/python')
        executable.parent.mkdir(parents=True)
        executable.write_text('#!/usr/bin/env bash\n'
                              'if [[ "$1" == "-c" && "$2" == *sys.version_info* ]]; then\n'
                              + ("printf '%s\\r\\n' " if report_crlf else 'echo ') + actual + '; exit 0; fi\n'
                              'echo SELECTED=' + actual + '\nexit 91\n')
        executable.chmod(0o755)
    native_bash = Path(r'C:\Program Files\Git\bin\bash.exe')
    bash = str(native_bash) if os.name == 'nt' and native_bash.exists() else shutil.which('bash')
    assert bash
    return subprocess.run([bash, 'build.sh'], cwd=tmp_path, timeout=15, capture_output=True, text=True,
                          env={**os.environ, 'BUILD_PYTHON_VERSION': requested, 'GITHUB_ACTIONS': 'false'})


def test_explicit_314_wins_with_both_venvs(tmp_path):
    result = build_preflight(tmp_path, {'313': '3.13', '314': '3.14'}, '3.14')
    assert 'SELECTED=3.14' in result.stdout
    assert 'SELECTED=3.13' not in result.stdout


def test_missing_requested_runtime_fails_early(tmp_path):
    result = build_preflight(tmp_path, {'313': '3.13'}, '3.14')
    assert result.returncode != 0
    assert 'Python 3.14 build environment not found' in result.stderr
    assert 'SELECTED=' not in result.stdout


def test_wrong_executable_version_is_rejected(tmp_path):
    result = build_preflight(tmp_path, {'314': '3.13'}, '3.14')
    assert result.returncode != 0
    assert 'Requested Python 3.14, found 3.13' in result.stderr
    assert 'SELECTED=' not in result.stdout


def test_unsupported_requested_runtime_is_rejected(tmp_path):
    result = build_preflight(tmp_path, {'314': '3.14'}, '3.12')
    assert result.returncode != 0
    assert 'BUILD_PYTHON_VERSION must be 3.13 or 3.14' in result.stderr


def test_default_windows_runtime_uses_verified_314(tmp_path):
    result = build_preflight(tmp_path, {'313': '3.13', '314': '3.14'}, '')
    assert 'SELECTED=3.14' in result.stdout
    assert 'SELECTED=3.13' not in result.stdout


def test_prepare_rejects_wrong_runtime_before_creating_venv(tmp_path):
    shutil.copy(ROOT / 'install.sh', tmp_path / 'install.sh')
    (tmp_path / 'scripts').mkdir()
    shutil.copy(ROOT / 'scripts/python_runtime.sh', tmp_path / 'scripts/python_runtime.sh')
    classifier = tmp_path / 'os_classifier.sh'
    classifier.write_text('#!/usr/bin/env bash\necho windows-x86_64\n')
    classifier.chmod(0o755)
    executable = tmp_path / 'candidate-python'
    executable.write_text('#!/usr/bin/env bash\necho 3.13\n')
    executable.chmod(0o755)
    native_bash = Path(r'C:\Program Files\Git\bin\bash.exe')
    bash = str(native_bash) if os.name == 'nt' and native_bash.exists() else shutil.which('bash')
    result = subprocess.run([bash, 'install.sh'], cwd=tmp_path, timeout=15, capture_output=True, text=True,
                            env={**os.environ, 'BUILD_PYTHON_VERSION': '3.14',
                                 'PYTHON': str(executable).replace('\\', '/')})
    assert result.returncode != 0
    assert 'Requested Python 3.14, found 3.13' in result.stderr
    assert not (tmp_path / 'build').exists()


def test_native_windows_crlf_version_report_is_accepted(tmp_path):
    result = build_preflight(tmp_path, {'314': '3.14'}, '3.14', report_crlf=True)
    assert 'SELECTED=3.14' in result.stdout


def test_explicit_313_rollback_remains_available(tmp_path):
    result = build_preflight(tmp_path, {'313': '3.13', '314': '3.14'}, '3.13')
    assert 'SELECTED=3.13' in result.stdout
    assert 'SELECTED=3.14' not in result.stdout
