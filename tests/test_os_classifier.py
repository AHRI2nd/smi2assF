import os
import subprocess


def test_intel_macos_is_not_a_supported_build_target(tmp_path):
    uname = tmp_path / 'uname'
    uname.write_text(
        '#!/bin/sh\n'
        'case "$1" in\n'
        '  -s) echo Darwin ;;\n'
        '  -m) echo x86_64 ;;\n'
        'esac\n',
        encoding='utf-8',
    )
    uname.chmod(0o755)
    environment = os.environ | {'PATH': f'{tmp_path}{os.pathsep}{os.environ["PATH"]}'}

    result = subprocess.run(
        ['bash', 'os_classifier.sh'],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )

    assert result.returncode != 0
    assert 'Intel Mac builds are not supported' in result.stderr
