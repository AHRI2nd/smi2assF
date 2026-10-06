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
