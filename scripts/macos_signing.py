#!/usr/bin/env python3
"""Prepare an isolated signing keychain and notarize macOS release artifacts."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Mapping, Sequence


class SigningError(RuntimeError):
    """A signing prerequisite, command, or verification failed."""


def _run(
    command: Sequence[str], label: str, *, timeout: int = 120,
    check: bool = True, private: bool = False,
) -> subprocess.CompletedProcess[str]:
    # Credential commands must never be logged by their arguments or exceptions.
    print(f'[macOS signing] START {label} (timeout: {timeout}s)', flush=True)
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace', start_new_session=True,
        )
    except OSError:
        raise SigningError(f'{label}: could not start required tool') from None
    while True:
        remaining = timeout - (time.monotonic() - started)
        try:
            stdout, stderr = process.communicate(timeout=max(0.01, min(30, remaining)))
            break
        except subprocess.TimeoutExpired:
            if time.monotonic() - started >= timeout:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                raise SigningError(f'{label}: timed out after {timeout}s') from None
            print(f'[macOS signing] WAIT {label} ({int(time.monotonic() - started)}s)', flush=True)
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    if check and result.returncode:
        details = '' if private else '\n' + (stdout + stderr).strip()
        raise SigningError(f'{label}: failed with exit code {result.returncode}{details}')
    print(f'[macOS signing] END {label} (exit code: {result.returncode})', flush=True)
    return result


def _required(environment: Mapping[str, str], names: Sequence[str]) -> None:
    missing = [name for name in names if not environment.get(name, '').strip()]
    if missing:
        raise SigningError('Missing macOS signing settings: ' + ', '.join(missing))


def select_identity(identity_text: str, team: str) -> str:
    identities = re.findall(
        r'^\s*\d+\)\s+([0-9A-Fa-f]{40})\s+"Developer ID Application: [^"\n]+ \(([^)]+)\)"',
        identity_text, re.MULTILINE,
    )
    matches = [identity for identity, owner in identities if owner == team]
    if len(matches) != 1:
        raise SigningError('Expected exactly one valid Developer ID Application identity with a private key for APPLE_TEAM_ID')
    return matches[0]


def _export(environment: Mapping[str, str], values: Mapping[str, str]) -> None:
    with Path(environment['GITHUB_ENV']).open('a', encoding='utf-8') as stream:
        for name, value in values.items():
            if '\n' in value or '\r' in value:
                raise SigningError(f'Invalid multiline signing setting: {name}')
            stream.write(f'{name}={value}\n')


def prepare(environment: Mapping[str, str]) -> None:
    _required(environment, (
        'APPLE_CERTIFICATE_P12_BASE64', 'APPLE_CERTIFICATE_PASSWORD', 'APPLE_ID',
        'APPLE_TEAM_ID', 'APPLE_APP_SPECIFIC_PASSWORD', 'RUNNER_TEMP', 'GITHUB_ENV',
    ))
    team = environment['APPLE_TEAM_ID'].strip()
    if not re.fullmatch(r'[A-Z0-9]{10}', team):
        raise SigningError('APPLE_TEAM_ID must contain 10 uppercase letters or digits')
    try:
        certificate = base64.b64decode(''.join(environment['APPLE_CERTIFICATE_P12_BASE64'].split()), validate=True)
    except (ValueError, binascii.Error):
        raise SigningError('APPLE_CERTIFICATE_P12_BASE64 is not valid Base64') from None
    if not certificate:
        raise SigningError('APPLE_CERTIFICATE_P12_BASE64 is empty')
    state = Path(tempfile.mkdtemp(prefix='smi2assf-signing-', dir=environment['RUNNER_TEMP']))
    keychain = state / 'signing.keychain-db'
    certificate_path = state / 'certificate.p12'
    password = secrets.token_urlsafe(32)
    cleanup_environment = {'MACOS_SIGNING_STATE_DIR': str(state)}
    try:
        # Export the directory first so the workflow can clean up after partial failure.
        _export(environment, cleanup_environment)
        previous = _run(['security', 'list-keychains', '-d', 'user'], 'read keychain search list')
        (state / 'previous-keychains.json').write_text(json.dumps(shlex.split(previous.stdout)), encoding='utf-8')
        certificate_path.write_bytes(certificate)
        certificate_path.chmod(0o600)
        _run(['security', 'create-keychain', '-p', password, str(keychain)], 'create temporary keychain', private=True)
        _run(['security', 'set-keychain-settings', '-lut', '21600', str(keychain)], 'configure temporary keychain')
        _run(['security', 'unlock-keychain', '-p', password, str(keychain)], 'unlock temporary keychain', private=True)
        _run([
            'security', 'import', str(certificate_path), '-P', environment['APPLE_CERTIFICATE_PASSWORD'],
            '-t', 'cert', '-f', 'pkcs12', '-k', str(keychain), '-T', '/usr/bin/codesign', '-T', '/usr/bin/security',
        ], 'import Developer ID certificate', private=True)
        certificate_path.unlink()
        _run(['security', 'set-key-partition-list', '-S', 'apple-tool:,apple:', '-s', '-k', password, str(keychain)], 'authorize codesign', private=True)
        original = json.loads((state / 'previous-keychains.json').read_text())
        _run(['security', 'list-keychains', '-d', 'user', '-s', str(keychain), *original], 'enable signing keychain')
        identities = _run(['security', 'find-identity', '-v', '-p', 'codesigning', str(keychain)], 'validate Developer ID identity')
        identity = select_identity(identities.stdout, team)
        _run([
            'xcrun', 'notarytool', 'store-credentials', 'smi2assF-notary',
            '--apple-id', environment['APPLE_ID'], '--team-id', team,
            '--password', environment['APPLE_APP_SPECIFIC_PASSWORD'],
            '--keychain', str(keychain), '--validate',
        ], 'validate and store notarization credentials', timeout=180, private=True)
        _export(environment, {
            'MACOS_CODESIGN_IDENTITY': identity, 'MACOS_EXPECTED_TEAM_ID': team,
            'MACOS_SIGNING_KEYCHAIN': str(keychain), 'MACOS_NOTARY_PROFILE': 'smi2assF-notary',
        })
    except Exception:
        cleanup(cleanup_environment)
        raise


def cleanup(environment: Mapping[str, str]) -> None:
    location = environment.get('MACOS_SIGNING_STATE_DIR')
    if not location:
        return
    state = Path(location)
    if not state.exists():
        return
    # Only remove the private directory created by prepare(), never an arbitrary path.
    if not state.name.startswith('smi2assf-signing-'):
        raise SigningError('Refusing to clean an unrelated signing directory')
    previous = state / 'previous-keychains.json'
    try:
        if previous.is_file():
            _run(['security', 'list-keychains', '-d', 'user', '-s', *json.loads(previous.read_text())], 'restore keychain search list')
    finally:
        try:
            _run(['security', 'delete-keychain', str(state / 'signing.keychain-db')], 'delete temporary keychain', check=False)
        finally:
            shutil.rmtree(state)


def validate_signature(display: str, team: str, *, require_runtime: bool) -> None:
    if not re.search(r'^Authority=Developer ID Application:', display, re.MULTILINE):
        raise SigningError('Artifact is not signed with Developer ID Application')
    if not re.search(r'^TeamIdentifier=' + re.escape(team) + r'$', display, re.MULTILINE):
        raise SigningError('Artifact signing team does not match APPLE_TEAM_ID')
    if not re.search(r'^Timestamp=.+$', display, re.MULTILINE):
        raise SigningError('Artifact signature has no secure timestamp')
    if require_runtime and '(runtime)' not in display:
        raise SigningError('App signature does not enable the hardened runtime')


def _verify_signature(path: Path, environment: Mapping[str, str], *, app: bool) -> None:
    arguments = ['codesign', '--verify', '--strict', '--verbose=2']
    if app:
        arguments.append('--deep')
    _run([*arguments, str(path)], 'verify artifact signature')
    display = _run(['codesign', '--display', '--verbose=4', str(path)], 'inspect artifact signature')
    validate_signature(display.stdout + display.stderr, environment['MACOS_EXPECTED_TEAM_ID'], require_runtime=app)


def notarize(path: Path, label: str, environment: Mapping[str, str]) -> None:
    authentication = ['--keychain-profile', environment['MACOS_NOTARY_PROFILE'], '--keychain', environment['MACOS_SIGNING_KEYCHAIN']]
    logs = Path('build/macos-signing-logs')
    logs.mkdir(parents=True, exist_ok=True)
    submitted = _run(['xcrun', 'notarytool', 'submit', str(path), *authentication, '--no-wait', '--output-format', 'json'], f'submit {label} for notarization', timeout=300)
    (logs / f'{label}-submission.json').write_text(submitted.stdout, encoding='utf-8')
    try:
        submission_id = str(uuid.UUID(json.loads(submitted.stdout)['id']))
    except (KeyError, ValueError, TypeError):
        raise SigningError(f'{label}: notarization did not return a valid submission ID') from None
    print(f'[macOS signing] {label} submission ID: {submission_id}', flush=True)
    try:
        result = _run([
            'xcrun', 'notarytool', 'wait', submission_id, *authentication,
            '--timeout', '20m', '--output-format', 'json',
        ], f'wait for {label} notarization', timeout=1260, check=False)
        (logs / f'{label}-result.json').write_text(result.stdout, encoding='utf-8')
        try:
            status = json.loads(result.stdout)['status']
        except (KeyError, ValueError, TypeError):
            raise SigningError(f'{label}: invalid notarization result; see diagnostic artifacts') from None
        if result.returncode or status != 'Accepted':
            raise SigningError(f'{label}: notarization status {status!r}, exit code {result.returncode}; see diagnostic artifacts')
    finally:
        try:
            log = _run(['xcrun', 'notarytool', 'log', submission_id, str(logs / f'{label}-notary-log.json'), *authentication], f'download {label} notary log', check=False)
            if log.returncode:
                (logs / f'{label}-log-error.txt').write_text(log.stderr or log.stdout, encoding='utf-8')
        except SigningError as error:
            (logs / f'{label}-log-error.txt').write_text(str(error), encoding='utf-8')


def _verify_notarized(path: Path, environment: Mapping[str, str], *, app: bool) -> None:
    _run(['xcrun', 'stapler', 'validate', str(path)], 'validate stapled ticket')
    _verify_signature(path, environment, app=app)
    assessment = ['spctl', '--assess', '--type', 'execute' if app else 'open', '--verbose=4']
    if not app:
        assessment.extend(['--context', 'context:primary-signature'])
    _run([*assessment, str(path)], 'verify Gatekeeper acceptance')
    if app and shutil.which('syspolicy_check'):
        _run(['syspolicy_check', 'distribution', str(path)], 'check app readiness for distribution')


def process_app(path: Path, environment: Mapping[str, str]) -> None:
    _verify_signature(path, environment, app=True)
    with tempfile.TemporaryDirectory(prefix='smi2assf-notary-') as folder:
        archive = Path(folder) / 'app.zip'
        _run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(path), str(archive)], 'archive signed app')
        notarize(archive, 'app', environment)
    _run(['xcrun', 'stapler', 'staple', str(path)], 'staple app ticket')
    _verify_notarized(path, environment, app=True)


def process_dmg(path: Path, environment: Mapping[str, str]) -> None:
    _run([
        'codesign', '--force', '--timestamp', '--sign', environment['MACOS_CODESIGN_IDENTITY'],
        '--keychain', environment['MACOS_SIGNING_KEYCHAIN'], str(path),
    ], 'sign distribution DMG')
    _verify_signature(path, environment, app=False)
    notarize(path, 'dmg', environment)
    _run(['xcrun', 'stapler', 'staple', str(path)], 'staple DMG ticket')
    _verify_notarized(path, environment, app=False)
    with tempfile.TemporaryDirectory(prefix='smi2assf-dmg-check-') as folder:
        mount = Path(folder) / 'volume'
        mount.mkdir()
        _run(['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', str(mount), str(path)], 'mount notarized DMG')
        try:
            app = mount / 'smi2assF.app'
            _verify_notarized(app, environment, app=True)
            _run([str(app / 'Contents/MacOS/smi2assF'), '--smoke-test'], 'smoke-test app inside notarized DMG', timeout=60)
        finally:
            _run(['hdiutil', 'detach', str(mount)], 'detach verified DMG')


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'cleanup', 'app', 'dmg'))
    parser.add_argument('path', nargs='?', type=Path)
    parsed = parser.parse_args(arguments)
    if sys.platform != 'darwin':
        parser.error('macOS signing requires a macOS runner')
    try:
        if parsed.action == 'prepare':
            prepare(os.environ)
        elif parsed.action == 'cleanup':
            cleanup(os.environ)
        else:
            if parsed.path is None:
                parser.error('app and dmg require an artifact path')
            _required(os.environ, ('MACOS_CODESIGN_IDENTITY', 'MACOS_EXPECTED_TEAM_ID', 'MACOS_SIGNING_KEYCHAIN', 'MACOS_NOTARY_PROFILE'))
            (process_app if parsed.action == 'app' else process_dmg)(parsed.path.resolve(), os.environ)
    except (SigningError, OSError) as error:
        print(f'[macOS signing] FAILED: {error}', file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
