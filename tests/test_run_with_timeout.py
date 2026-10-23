import subprocess
import sys
import time
import os
import signal

import pytest

from scripts.run_with_timeout import run_with_timeout


def test_run_with_timeout_returns_success_exit_code(capsys):
    result = run_with_timeout([sys.executable, '-c', 'pass'], 5, 'quick command')
    output = capsys.readouterr().out

    assert result == 0
    assert '[build] START quick command' in output
    assert '[build] DONE quick command' in output


def test_run_with_timeout_stops_a_hung_command(capsys):
    started = time.monotonic()

    result = run_with_timeout([sys.executable, '-c', 'import time; time.sleep(30)'], 0.2, 'hung command')

    assert result == 124
    assert time.monotonic() - started < 5
    assert '[build] TIMEOUT hung command' in capsys.readouterr().err


def test_run_with_timeout_stops_descendant_processes(tmp_path):
    marker = tmp_path / 'child-survived-timeout'
    child_code = f'import time; time.sleep(0.8); open({str(marker)!r}, "w").close()'
    parent_code = (
        'import subprocess, sys, time; '
        f'subprocess.Popen([sys.executable, "-c", {child_code!r}]); '
        'time.sleep(30)'
    )

    result = run_with_timeout([sys.executable, '-c', parent_code], 0.2, 'parent with child')
    time.sleep(0.9)

    assert result == 124
    assert not marker.exists()


def test_run_with_timeout_preserves_command_failure():
    result = run_with_timeout([sys.executable, '-c', 'raise SystemExit(7)'], 5, 'failing command')

    assert result == 7


@pytest.mark.skipif(os.name == 'nt', reason='POSIX process-group signal handling')
def test_timeout_kills_resistant_child_after_parent_exits(tmp_path):
    pidfile = tmp_path / 'owned-child.pid'
    marker = tmp_path / 'child-executed-after-timeout'
    child = (
        'import os,signal,time,pathlib; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
        f'pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid())); '
        f'time.sleep(2); pathlib.Path({str(marker)!r}).touch(); time.sleep(30)'
    )
    parent = f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{child!r}]); time.sleep(30)'
    try:
        assert run_with_timeout([sys.executable, '-c', parent], 1, 'resistant child') == 124
        assert pidfile.exists(), 'The child must start for this regression to be exercised'
        time.sleep(1.3)
        assert not marker.exists()
    finally:
        if pidfile.exists():
            try:
                os.kill(int(pidfile.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_run_with_timeout_cli_accepts_arguments_after_separator():
    result = subprocess.run(
        [
            sys.executable,
            'scripts/run_with_timeout.py',
            '--timeout-seconds',
            '5',
            '--label',
            'cli command',
            '--',
            sys.executable,
            '-c',
            'pass',
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '[build] DONE cli command' in result.stdout
