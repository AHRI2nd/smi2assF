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
