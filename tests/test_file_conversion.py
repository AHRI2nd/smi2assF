from pathlib import Path

from smi2ass import convert_smi_file


def test_convert_smi_file_returns_written_outputs_and_repair_diagnostics(tmp_path):
    source = tmp_path / 'episode.smi'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>First cue\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )

    result = convert_smi_file(source)

    output = tmp_path / 'episode.kor.ass'
    assert result.source == source
    assert result.outputs == (output,)
    assert output.is_file()
    assert 'First cue' in output.read_text(encoding='utf-8')


def test_convert_smi_file_can_omit_language_suffix_for_single_language(tmp_path):
    source = tmp_path / 'episode.smi'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>First cue\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )

    result = convert_smi_file(source, include_language_suffix=False)

    output = tmp_path / 'episode.ass'
    assert result.outputs == (output,)
    assert output.is_file()


def test_convert_smi_file_keeps_language_suffix_for_multiple_languages(tmp_path):
    source = tmp_path / 'episode.smi'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>Korean\n'
        '<P Class=ENCC>English\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;<P Class=ENCC>&nbsp;',
        encoding='utf-8',
    )

    result = convert_smi_file(source, include_language_suffix=False)

    assert {path.name for path in result.outputs} == {'episode.kor.ass', 'episode.eng.ass'}
    assert any(item.code == 'SYNC_CLOSE_INSERTED' for item in result.diagnostics)


def test_convert_smi_file_can_preserve_existing_output(tmp_path):
    source = tmp_path / 'episode.smi'
    output = tmp_path / 'episode.kor.ass'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>New cue\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )
    output.write_text('Keep the existing file', encoding='utf-8')

    result = convert_smi_file(source, overwrite=False)

    assert result.outputs == ()
    assert result.skipped_existing == (output,)
    assert output.read_text(encoding='utf-8') == 'Keep the existing file'


def test_convert_smi_file_writes_missing_languages_when_one_output_exists(tmp_path):
    source = tmp_path / 'multi.smi'
    existing = tmp_path / 'multi.eng.ass'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>한국어\n'
        '<SYNC Start=0><P Class=ENCC>English\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;\n'
        '<SYNC Start=1000><P Class=ENCC>&nbsp;',
        encoding='utf-8',
    )
    existing.write_text('Preserve this output', encoding='utf-8')

    result = convert_smi_file(source, overwrite=False)

    korean = tmp_path / 'multi.kor.ass'
    assert result.outputs == (korean,)
    assert result.skipped_existing == (existing,)
    assert korean.is_file()
    assert '한국어' in korean.read_text(encoding='utf-8')
    assert existing.read_text(encoding='utf-8') == 'Preserve this output'


def test_invalid_bytes_are_reported(tmp_path, monkeypatch):
    import smi2ass
    source = tmp_path / 'invalid.smi'
    source.write_bytes(b'<SYNC Start=0><P Class=KRCC>bad\xff<SYNC Start=1000><P Class=KRCC>&nbsp;')
    monkeypatch.setattr(smi2ass.chardet, 'detect', lambda data: {'encoding': 'utf-8'})
    result = convert_smi_file(source)
    assert any(d.code == 'ENCODING_REPLACEMENT' and d.severity == 'skip' for d in result.diagnostics)
    assert '\ufffd' in result.outputs[0].read_text(encoding='utf-8')


def test_input_is_read_once(tmp_path, monkeypatch):
    import builtins
    source = tmp_path / 'once.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC>Keep<SYNC Start=1000><P Class=KRCC>&nbsp;', encoding='utf-8')
    original = builtins.open
    reads = []
    def open_file(path, *args, **kwargs):
        if Path(path) == source:
            reads.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(builtins, 'open', open_file)
    convert_smi_file(source)
    assert len(reads) == 1


def test_detected_encoding_is_unavailable(tmp_path, monkeypatch):
    import pytest
    import smi2ass
    source = tmp_path / 'unknown.smi'
    source.write_bytes(b'caption')
    monkeypatch.setattr(smi2ass.chardet, 'detect', lambda data: {'encoding': 'not-an-encoding'})
    with pytest.raises(OSError, match='encoding'):
        convert_smi_file(source)
