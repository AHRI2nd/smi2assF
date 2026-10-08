import base64
import importlib
import json
import os
import subprocess
from pathlib import Path

import pytest


IDENTITY = 'A' * 40
TEAM = 'ABCD123456'
SUBMISSION = '12345678-1234-1234-1234-123456789012'


def signing_module():
    return importlib.import_module('scripts.macos_signing')


def signing_environment(tmp_path):
    return {
        'MACOS_CODESIGN_IDENTITY': IDENTITY,
        'MACOS_EXPECTED_TEAM_ID': TEAM,
        'MACOS_SIGNING_KEYCHAIN': str(tmp_path / 'signing.keychain-db'),
        'MACOS_NOTARY_PROFILE': 'smi2assF-notary',
    }


def test_prepare_rejects_missing_credentials_before_creating_files(tmp_path):
    signing = signing_module()
    with pytest.raises(signing.SigningError, match='APPLE_CERTIFICATE_P12_BASE64'):
        signing.prepare({'RUNNER_TEMP': str(tmp_path)})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('identity_text', [
    f'  1) {IDENTITY} "Apple Development: Example ({TEAM})"',
    f'  1) {IDENTITY} "Developer ID Application: Example (OTHER12345)"',
    '  0 valid identities found',
])
def test_identity_rejects_wrong_certificate_or_team(identity_text):
    signing = signing_module()
    with pytest.raises(signing.SigningError):
        signing.select_identity(identity_text, TEAM)


def test_identity_selects_matching_developer_id_private_key():
    signing = signing_module()
    assert signing.select_identity(
        f'  1) {IDENTITY} "Developer ID Application: Example ({TEAM})"\n'
        '     1 valid identities found', TEAM,
    ) == IDENTITY


def test_prepare_imports_secret_into_temporary_keychain_and_removes_p12(tmp_path, monkeypatch):
    signing = signing_module()
    environment = {
        'RUNNER_TEMP': str(tmp_path),
        'GITHUB_ENV': str(tmp_path / 'github-env'),
        'APPLE_CERTIFICATE_P12_BASE64': base64.b64encode(b'private certificate').decode(),
        'APPLE_CERTIFICATE_PASSWORD': 'certificate-secret',
        'APPLE_ID': 'developer@example.com',
        'APPLE_TEAM_ID': TEAM,
        'APPLE_APP_SPECIFIC_PASSWORD': 'notary-secret',
    }
    commands = []

    def native_run(command, label, **kwargs):
        commands.append(command)
        output = ''
        if command[:3] == ['security', 'list-keychains', '-d'] and '-s' not in command:
            output = '"/tmp/original-login.keychain-db"\n'
        if 'find-identity' in command:
            output = f'  1) {IDENTITY} "Developer ID Application: Example ({TEAM})"'
        return subprocess.CompletedProcess(command, 0, output, '')

    monkeypatch.setattr(signing, '_run', native_run)
    signing.prepare(environment)
    exported = dict(line.split('=', 1) for line in (tmp_path / 'github-env').read_text().splitlines())
    state = Path(exported['MACOS_SIGNING_STATE_DIR'])
    assert exported['MACOS_CODESIGN_IDENTITY'] == IDENTITY
    assert exported['MACOS_EXPECTED_TEAM_ID'] == TEAM
    assert not list(state.glob('*.p12'))
    assert json.loads((state / 'previous-keychains.json').read_text()) == ['/tmp/original-login.keychain-db']
    assert any(command[:2] == ['security', 'import'] and '-T' in command for command in commands)
    assert any(command[:3] == ['xcrun', 'notarytool', 'store-credentials'] and '--validate' in command for command in commands)
    assert 'certificate-secret' not in (tmp_path / 'github-env').read_text()
    assert 'notary-secret' not in (tmp_path / 'github-env').read_text()
    signing.cleanup(exported)
    assert not state.exists()
    assert ['security', 'list-keychains', '-d', 'user', '-s', '/tmp/original-login.keychain-db'] in commands


def test_invalid_base64_is_rejected_before_keychain_creation(tmp_path):
    signing = signing_module()
    environment = {
        'RUNNER_TEMP': str(tmp_path), 'GITHUB_ENV': str(tmp_path / 'github-env'),
        'APPLE_CERTIFICATE_P12_BASE64': 'not base64!',
        'APPLE_CERTIFICATE_PASSWORD': 'secret', 'APPLE_ID': 'developer@example.com',
        'APPLE_TEAM_ID': TEAM, 'APPLE_APP_SPECIFIC_PASSWORD': 'notary-secret',
    }
    with pytest.raises(signing.SigningError, match='Base64'):
        signing.prepare(environment)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('display', [
    f'Authority=Developer ID Application: Example ({TEAM})\nTeamIdentifier={TEAM}\nTimestamp=today',
    'flags=0x10000(runtime)\nSignature=adhoc\nTeamIdentifier=not set\nTimestamp=today',
    f'flags=0x10000(runtime)\nAuthority=Developer ID Application: Example ({TEAM})\nTeamIdentifier={TEAM}',
    'flags=0x10000(runtime)\nAuthority=Developer ID Application: Example (OTHER12345)\nTeamIdentifier=OTHER12345\nTimestamp=today',
])
def test_bundle_signature_requires_runtime_timestamp_and_expected_team(display):
    signing = signing_module()
    with pytest.raises(signing.SigningError):
        signing.validate_signature(display, TEAM, require_runtime=True)


def test_notarization_acceptance_staples_and_verifies_app(tmp_path, monkeypatch):
    signing = signing_module()
    monkeypatch.chdir(tmp_path)
    app = tmp_path / 'smi2assF.app'
    app.mkdir()
    commands = []

    def native_run(command, label, **kwargs):
        commands.append(command)
        output = ''
        error = ''
        if command[:2] == ['codesign', '--display']:
            error = f'flags=0x10000(runtime)\nAuthority=Developer ID Application: Example ({TEAM})\nTeamIdentifier={TEAM}\nTimestamp=today'
        if command[:3] == ['xcrun', 'notarytool', 'submit']:
            output = json.dumps({'id': SUBMISSION, 'message': 'Successfully uploaded file', 'name': 'app.zip'})
        if command[:3] == ['xcrun', 'notarytool', 'wait']:
            assert '--timeout' in command
            assert kwargs['timeout'] <= 1260
            output = json.dumps({'id': SUBMISSION, 'status': 'Accepted', 'message': 'Processing complete'})
        if command[:3] == ['xcrun', 'notarytool', 'log']:
            Path(command[4]).write_text(json.dumps({'jobId': SUBMISSION, 'status': 'Accepted', 'issues': None}))
        return subprocess.CompletedProcess(command, 0, output, error)

    monkeypatch.setattr(signing, '_run', native_run)
    signing.process_app(app, signing_environment(tmp_path))
    assert ['xcrun', 'stapler', 'staple', str(app)] in commands
    assert ['xcrun', 'stapler', 'validate', str(app)] in commands
    assert any(command[:3] == ['spctl', '--assess', '--type'] and 'execute' in command for command in commands)
    report = json.loads((tmp_path / 'build/macos-signing-logs/app-result.json').read_text())
    assert report['status'] == 'Accepted'
    assert all('--password' not in command for command in commands)


@pytest.mark.parametrize('status, exit_code', [('Invalid', 0), ('In Progress', 0), ('Accepted', 1)])
def test_unaccepted_or_failed_notary_wait_never_staples(tmp_path, monkeypatch, status, exit_code):
    signing = signing_module()
    monkeypatch.chdir(tmp_path)
    commands = []

    def native_run(command, label, **kwargs):
        commands.append(command)
        output = ''
        code = 0
        if command[:3] == ['xcrun', 'notarytool', 'submit']:
            output = json.dumps({'id': SUBMISSION, 'message': 'Successfully uploaded file', 'name': 'app.zip'})
        if command[:3] == ['xcrun', 'notarytool', 'wait']:
            output = json.dumps({'id': SUBMISSION, 'status': status, 'message': 'Processing complete'})
            code = exit_code
        return subprocess.CompletedProcess(command, code, output, '')

    monkeypatch.setattr(signing, '_run', native_run)
    with pytest.raises(signing.SigningError):
        signing.notarize(tmp_path / 'app.zip', 'app', signing_environment(tmp_path))
    assert not any(command[:2] == ['xcrun', 'stapler'] for command in commands)
    assert (tmp_path / 'build/macos-signing-logs/app-submission.json').is_file()
    assert any(command[:3] == ['xcrun', 'notarytool', 'log'] for command in commands)


def test_private_command_failure_does_not_echo_secret(monkeypatch, capsys):
    signing = signing_module()
    with pytest.raises(signing.SigningError) as error:
        signing._run(
            ['definitely-missing-macos-tool', '--password', 'private-value'],
            'credential setup', private=True,
        )
    output = capsys.readouterr()
    assert 'private-value' not in str(error.value) + output.out + output.err


def test_failed_credential_import_cleans_temporary_state(tmp_path, monkeypatch):
    signing = signing_module()
    environment = {
        'RUNNER_TEMP': str(tmp_path), 'GITHUB_ENV': str(tmp_path / 'github-env'),
        'APPLE_CERTIFICATE_P12_BASE64': base64.b64encode(b'private certificate').decode(),
        'APPLE_CERTIFICATE_PASSWORD': 'secret', 'APPLE_ID': 'developer@example.com',
        'APPLE_TEAM_ID': TEAM, 'APPLE_APP_SPECIFIC_PASSWORD': 'notary-secret',
    }
    commands = []

    def native_run(command, label, **kwargs):
        commands.append(command)
        if command[:2] == ['security', 'import']:
            raise signing.SigningError('import failed')
        output = '"/tmp/login.keychain-db"' if command[:2] == ['security', 'list-keychains'] and '-s' not in command else ''
        return subprocess.CompletedProcess(command, 0, output, '')

    monkeypatch.setattr(signing, '_run', native_run)
    with pytest.raises(signing.SigningError, match='import failed'):
        signing.prepare(environment)
    assert not list(tmp_path.glob('smi2assf-signing-*'))
    assert any(command[:2] == ['security', 'delete-keychain'] for command in commands)


def test_notary_timeout_preserves_submission_and_requests_diagnostics(tmp_path, monkeypatch):
    signing = signing_module()
    monkeypatch.chdir(tmp_path)
    commands = []

    def native_run(command, label, **kwargs):
        commands.append(command)
        if command[:3] == ['xcrun', 'notarytool', 'wait']:
            raise signing.SigningError('notarization timed out')
        return subprocess.CompletedProcess(command, 0, json.dumps({'id': SUBMISSION}), '')

    monkeypatch.setattr(signing, '_run', native_run)
    with pytest.raises(signing.SigningError, match='timed out'):
        signing.notarize(tmp_path / 'app.zip', 'app', signing_environment(tmp_path))
    assert json.loads((tmp_path / 'build/macos-signing-logs/app-submission.json').read_text())['id'] == SUBMISSION
    assert any(command[:3] == ['xcrun', 'notarytool', 'log'] for command in commands)


def test_dmg_verifies_enclosed_app_and_detaches_after_smoke_failure(tmp_path, monkeypatch):
    signing = signing_module()
    monkeypatch.chdir(tmp_path)
    dmg = tmp_path / 'smi2assF.osx-arm64.dmg'
    commands = []

    def native_run(command, label, **kwargs):
        commands.append(command)
        output = ''
        error = ''
        if command[:2] == ['codesign', '--display']:
            error = f'flags=0x10000(runtime)\nAuthority=Developer ID Application: Example ({TEAM})\nTeamIdentifier={TEAM}\nTimestamp=today'
        if command[:3] == ['xcrun', 'notarytool', 'submit']:
            output = json.dumps({'id': SUBMISSION})
        if command[:3] == ['xcrun', 'notarytool', 'wait']:
            output = json.dumps({'id': SUBMISSION, 'status': 'Accepted'})
        if '--smoke-test' in command:
            raise signing.SigningError('smoke failed')
        return subprocess.CompletedProcess(command, 0, output, error)

    monkeypatch.setattr(signing, '_run', native_run)
    with pytest.raises(signing.SigningError, match='smoke failed'):
        signing.process_dmg(dmg, signing_environment(tmp_path))
    assert ['xcrun', 'stapler', 'staple', str(dmg)] in commands
    assert any(command[:2] == ['hdiutil', 'detach'] for command in commands)
    assert any(command[:2] == ['spctl', '--assess'] and Path(command[-1]).name == 'smi2assF.app' for command in commands)


@pytest.mark.skipif(os.name == 'nt', reason='The macOS native command runner uses POSIX process groups.')
def test_command_timeout_terminates_with_a_bounded_error():
    import sys

    signing = signing_module()
    with pytest.raises(signing.SigningError, match='timed out'):
        signing._run([sys.executable, '-c', 'import time; time.sleep(5)'], 'slow tool', timeout=1)


@pytest.mark.skipif(os.name == 'nt', reason='Requires a POSIX shell.')
def test_github_macos_build_cannot_disable_release_signing(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'build.sh'
    (tmp_path / 'build.sh').write_text(script.read_text())
    classifier = tmp_path / 'os_classifier.sh'
    classifier.write_text('#!/bin/sh\nprintf "osx-arm64\\n"\n')
    classifier.chmod(0o755)
    environment = {**os.environ, 'GITHUB_ACTIONS': 'true', 'MACOS_RELEASE_SIGNING': '0'}
    result = subprocess.run(['bash', 'build.sh'], cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'requires MACOS_RELEASE_SIGNING=1' in result.stderr
    assert 'Run install.sh' not in result.stderr


@pytest.mark.skipif(os.name == 'nt', reason='Requires a POSIX shell.')
@pytest.mark.parametrize('fail_stage', ['', 'app', 'dmg'])
def test_signed_build_checksums_only_after_both_notarization_stages(tmp_path, fail_stage):
    import sys

    script = Path(__file__).resolve().parents[1] / 'build.sh'
    (tmp_path / 'build.sh').write_text(script.read_text())
    classifier = tmp_path / 'os_classifier.sh'
    classifier.write_text('#!/bin/sh\nprintf "osx-arm64\\n"\n')
    classifier.chmod(0o755)
    fake_python = tmp_path / 'build/venv-py314/bin/python'
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text(f'#!{sys.executable}\n' + r'''
import os
from pathlib import Path
import sys
arguments = sys.argv[1:]
if arguments[:2] == ['scripts/build_icon_path.py', 'osx-arm64']:
    print('/tmp/icon.icns')
elif arguments[:2] == ['-m', 'PyInstaller']:
    assert arguments[arguments.index('--codesign-identity') + 1] == 'A' * 40
    binary = Path('build/gui-stage/smi2assF.app/Contents/MacOS/smi2assF')
    binary.parent.mkdir(parents=True)
    binary.write_text('#!/bin/sh\nexit 0\n')
    binary.chmod(0o755)
elif arguments[:2] == ['-m', 'scripts.macos_signing']:
    with Path('stage-order').open('a') as stream:
        stream.write(arguments[2] + '\n')
    if os.environ['FAIL_SIGNING_STAGE'] == arguments[2]:
        raise SystemExit(1)
''')
    fake_python.chmod(0o755)
    bin_path = tmp_path / 'native-bin'
    bin_path.mkdir()
    ditto = bin_path / 'ditto'
    ditto.write_text('#!/bin/sh\ncp -R "$1" "$2"\n')
    ditto.chmod(0o755)
    hdiutil = bin_path / 'hdiutil'
    hdiutil.write_text(f'#!{sys.executable}\nimport sys\nfrom pathlib import Path\nPath(sys.argv[-1]).write_text("disk image")\n')
    hdiutil.chmod(0o755)
    dist = tmp_path / 'build/gui-dist'
    dist.mkdir()
    checksum = dist / 'smi2assF.osx-arm64.dmg.sha256'
    checksum.write_text('stale checksum')
    environment = {
        **os.environ, **signing_environment(tmp_path),
        'PATH': str(bin_path) + os.pathsep + os.environ['PATH'],
        'GITHUB_ACTIONS': 'true', 'MACOS_RELEASE_SIGNING': '1',
        'FAIL_SIGNING_STAGE': fail_stage,
    }
    result = subprocess.run(['bash', 'build.sh'], cwd=tmp_path, env=environment, capture_output=True, text=True)
    order = (tmp_path / 'stage-order').read_text().splitlines()
    if fail_stage:
        assert result.returncode != 0
        assert not checksum.exists()
        assert order == (['app'] if fail_stage == 'app' else ['app', 'dmg'])
    else:
        assert result.returncode == 0, result.stderr
        assert order == ['app', 'dmg']
        assert checksum.read_text() == '0bb2f0f3ed953c47d835a7adaefd95afa328e30a5c80fdce417dd12b014ad602  smi2assF.osx-arm64.dmg\n'
