import hashlib
import io
import tarfile

import pytest

from scripts.prepare_tkdnd import (
    TKDND_FILES,
    ensure_windows_tcl9_package_index,
    install_tkdnd_archive,
    needs_tcl9_intel_binary,
)


def test_tcl9_binary_is_only_needed_for_intel_macos():
    assert needs_tcl9_intel_binary('Darwin', 'x86_64', 9)
    assert not needs_tcl9_intel_binary('Darwin', 'arm64', 9)
    assert not needs_tcl9_intel_binary('Darwin', 'x86_64', 8)
    assert not needs_tcl9_intel_binary('Windows', 'AMD64', 9)


def test_windows_tcl9_directory_gets_package_index_when_missing(tmp_path):
    tkdnd_directory = tmp_path / 'tkdnd'
    source_index = tkdnd_directory / 'win-x64' / 'pkgIndex.tcl'
    target_index = tkdnd_directory / 'win-x64-tcl9' / 'pkgIndex.tcl'
    source_index.parent.mkdir(parents=True)
    target_index.parent.mkdir(parents=True)
    source_index.write_text('package index fixture', encoding='utf-8')

    repaired = ensure_windows_tcl9_package_index(tkdnd_directory)

    assert repaired is True
    assert target_index.read_text(encoding='utf-8') == 'package index fixture'


def _make_tkdnd_archive(entries=None):
    entries = entries or {filename: b'fixture' for filename in TKDND_FILES}
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        directory = tarfile.TarInfo('tkdnd2.9.5/')
        directory.type = tarfile.DIRTYPE
        archive.addfile(directory)
        for filename, payload in entries.items():
            item = tarfile.TarInfo('tkdnd2.9.5/' + filename)
            item.size = len(payload)
            archive.addfile(item, io.BytesIO(payload))
    return stream.getvalue()


def test_install_tkdnd_archive_checks_digest_and_stages_files(tmp_path):
    payload = _make_tkdnd_archive()
    target = tmp_path / 'tkdnd' / 'osx-x64-tcl9'

    install_tkdnd_archive(
        payload,
        target,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert {path.name for path in target.iterdir()} == TKDND_FILES
    assert (target / 'libtcl9tkdnd2.9.5.dylib').read_bytes() == b'fixture'


def test_install_tkdnd_archive_rejects_bad_digest(tmp_path):
    payload = _make_tkdnd_archive()

    with pytest.raises(ValueError, match='SHA-256'):
        install_tkdnd_archive(payload, tmp_path / 'tkdnd', expected_sha256='0' * 64)


def test_install_tkdnd_archive_rejects_unexpected_archive_paths(tmp_path):
    payload = _make_tkdnd_archive({'../outside.txt': b'bad'})

    with pytest.raises(ValueError, match='unexpected archive contents'):
        install_tkdnd_archive(
            payload,
            tmp_path / 'tkdnd',
            expected_sha256=hashlib.sha256(payload).hexdigest(),
        )

    assert not (tmp_path / 'outside.txt').exists()
