#!/usr/bin/env python3
"""Run a command with progress output and terminate its process tree on timeout."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from collections.abc import Sequence


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if os.name == 'nt':
        try:
            subprocess.run(
                ['taskkill', '/PID', str(process.pid), '/T', '/F'],
                check=False,
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run_with_timeout(
    command: Sequence[str],
    timeout_seconds: float,
    label: str,
) -> int:
    if timeout_seconds <= 0:
        raise ValueError('timeout_seconds must be greater than zero')
    if not command:
        raise ValueError('command must not be empty')

    print(f'[build] START {label} (timeout: {timeout_seconds:g}s)', flush=True)
    popen_options: dict[str, object] = {}
    if os.name == 'nt':
        popen_options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_options['start_new_session'] = True

    try:
        process = subprocess.Popen(command, **popen_options)
    except OSError as error:
        print(f'[build] FAILED {label}: {error}', file=sys.stderr, flush=True)
        return 127

    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        print(f'[build] TIMEOUT {label} after {timeout_seconds:g}s; terminating process tree', file=sys.stderr, flush=True)
        _terminate_process_tree(process)
        return 124

    if return_code == 0:
        print(f'[build] DONE {label}', flush=True)
    else:
        print(f'[build] FAILED {label} (exit code: {return_code})', file=sys.stderr, flush=True)
    return return_code


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout-seconds', type=float, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    parsed = parser.parse_args(arguments)
    command = parsed.command
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        parser.error('a command must follow --')
    return run_with_timeout(command, parsed.timeout_seconds, parsed.label)


if __name__ == '__main__':
    raise SystemExit(main())
