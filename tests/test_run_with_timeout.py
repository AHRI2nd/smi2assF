import subprocess
import sys
import time

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
