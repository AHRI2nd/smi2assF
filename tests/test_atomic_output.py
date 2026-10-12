"""Publication failures must never truncate a previously published subtitle."""
import errno
import os
from pathlib import Path
import subprocess
import sys

import smi2ass


def source_file(tmp_path):
    source = tmp_path / 'episode.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC>New cue<SYNC Start=1000><P Class=KRCC>&nbsp;', encoding='utf-8')
    return source, source.with_suffix('.kor.ass')


def test_partial_write_keeps_original(tmp_path, monkeypatch):
    source, target = source_file(tmp_path)
    target.write_bytes(b'original subtitle')
    def full_disk(fd):
        raise OSError(errno.ENOSPC, 'disk full')
    monkeypatch.setattr(os, 'fsync', full_disk)
    result = smi2ass.convert_smi_file(source)
    assert target.read_bytes() == b'original subtitle'
    assert result.outputs == ()
    assert any(d.code == 'OUTPUT_WRITE_FAILED' for d in result.diagnostics)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['episode.kor.ass', 'episode.smi']


def test_termination_before_publish_keeps_original(tmp_path):
    source, target = source_file(tmp_path)
    target.write_bytes(b'original subtitle')
    script = 'import os,sys; from smi2ass import convert_smi_file; os.fsync=lambda fd: os._exit(23); convert_smi_file(sys.argv[1])'
    child = subprocess.run([sys.executable, '-c', script, str(source)], timeout=20, capture_output=True)
    assert target.read_bytes() == b'original subtitle'
    assert child.returncode == 23


def test_concurrent_output_survives_no_overwrite(tmp_path, monkeypatch):
    source, target = source_file(tmp_path)
    original_exists = Path.exists
    def exists(path):
        present = original_exists(path)
        if path == target and not present:
            target.write_bytes(b'concurrent output')
        return present
    original_link = os.link
    def link(src, dst, *args, **kwargs):
        Path(dst).write_bytes(b'concurrent output')
        return original_link(src, dst, *args, **kwargs)
    original_rename = os.rename
    def rename(src, dst):
        Path(dst).write_bytes(b'concurrent output')
        return original_rename(src, dst)
    monkeypatch.setattr(os, 'rename', rename)
    monkeypatch.setattr(Path, 'exists', exists)
    monkeypatch.setattr(os, 'link', link)
    result = smi2ass.convert_smi_file(source, overwrite=False)
    assert target.read_bytes() == b'concurrent output'
    assert result.outputs == ()
    assert result.skipped_existing == (target,)


def test_failed_publication_keeps_original(tmp_path, monkeypatch):
    source, target = source_file(tmp_path)
    target.write_bytes(b'original subtitle')
    def denied(*args):
        raise PermissionError('publication denied')
    monkeypatch.setattr(os, 'replace', denied)
    result = smi2ass.convert_smi_file(source)
    assert target.read_bytes() == b'original subtitle'
    assert not result.outputs


def test_directory_output_is_failure(tmp_path):
    source, target = source_file(tmp_path)
    target.mkdir()
    result = smi2ass.convert_smi_file(source, overwrite=False)
    assert not result.skipped_existing
    assert any(d.code == 'OUTPUT_PATH_UNSAFE' for d in result.diagnostics)


def test_link_target_is_unchanged(tmp_path):
    import pytest
    source, target = source_file(tmp_path)
    victim = tmp_path / 'unrelated.txt'
    victim.write_bytes(b'untouched')
    try:
        target.symlink_to(victim)
    except OSError:
        pytest.skip('Symlink creation privilege unavailable')
    for overwrite in (False, True):
        result = smi2ass.convert_smi_file(source, overwrite=overwrite)
        assert not result.outputs and not result.skipped_existing
        assert any(d.code == 'OUTPUT_PATH_UNSAFE' for d in result.diagnostics)
    assert victim.read_bytes() == b'untouched'


def test_batch_output_collision_is_reported(tmp_path, monkeypatch):
    from smi2ass_gui_support import convert_smi_files
    source, target = source_file(tmp_path)
    other = tmp_path / 'other.smi'
    other.write_bytes(source.read_bytes())
    original = Path.with_name
    def with_name(path, name):
        return target if name.endswith('.ass') else original(path, name)
    monkeypatch.setattr(Path, 'with_name', with_name)
    summary = convert_smi_files([source, other], overwrite=True)
    assert summary.outputs == 1 and summary.failed == 1


def test_preserved_output_does_not_need_writable_directory(tmp_path, monkeypatch):
    import tempfile
    source, target = source_file(tmp_path)
    target.write_bytes(b'preserved output')
    def denied(*args, **kwargs):
        raise PermissionError('Cannot create files in this directory')
    monkeypatch.setattr(tempfile, 'mkstemp', denied)
    result = smi2ass.convert_smi_file(source, overwrite=False)
    assert result.skipped_existing == (target,)
    assert not result.outputs
    assert not any(d.severity == 'skip' for d in result.diagnostics)
    assert target.read_bytes() == b'preserved output'


def test_actual_partial_staging_failure_keeps_original(tmp_path, monkeypatch):
    source, target = source_file(tmp_path)
    target.write_bytes(b'original subtitle')
    original = os.fdopen
    class BrokenStream:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def write(self, contents):
            self.stream.write(contents[:17])
            raise OSError(errno.ENOSPC, 'disk full during write')
    monkeypatch.setattr(os, 'fdopen', lambda *args: BrokenStream(original(*args)))
    result = smi2ass.convert_smi_file(source)
    assert target.read_bytes() == b'original subtitle'
    assert not result.outputs
    assert any(d.code == 'OUTPUT_WRITE_FAILED' for d in result.diagnostics)
    assert len(list(tmp_path.iterdir())) == 2


def test_unsupported_no_replace_publication_fails_safely(tmp_path, monkeypatch):
    source, target = source_file(tmp_path)
    operation = 'rename' if os.name == 'nt' else 'link'
    def unsupported(*args):
        raise OSError(errno.ENOTSUP, 'No atomic publication on this volume')
    monkeypatch.setattr(os, operation, unsupported)
    result = smi2ass.convert_smi_file(source, overwrite=False)
    assert not target.exists()
    assert not result.outputs and not result.skipped_existing
    assert any(d.code == 'OUTPUT_WRITE_FAILED' for d in result.diagnostics)
    assert list(tmp_path.iterdir()) == [source]


def test_valid_long_filename_can_be_published(tmp_path):
    import pytest
    source = tmp_path / ('a' * 240 + '.smi')
    target = source.with_suffix('.kor.ass')
    try:
        source.write_text('<SYNC Start=0><P Class=KRCC>Keep<SYNC Start=1000><P Class=KRCC>&nbsp;', encoding='utf-8')
        target.write_bytes(b'original')
    except OSError as error:
        if error.errno == errno.ENAMETOOLONG or getattr(error, 'winerror', None) == 206:
            pytest.skip('Filesystem does not support this valid long input/output path')
        raise
    result = smi2ass.convert_smi_file(source)
    assert result.outputs == (target,)
    assert b'Keep' in target.read_bytes()
