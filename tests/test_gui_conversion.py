from smi2ass_gui_support import convert_smi_files


def test_convert_smi_files_processes_dropped_files_and_counts_outputs(tmp_path):
    source = tmp_path / 'episode.smi'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>First cue\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )

    summary = convert_smi_files([source], overwrite=False)

    assert summary.total == 1
    assert summary.outputs == 1
    assert summary.existing == 0
    assert summary.failed == 0
    assert (tmp_path / 'episode.kor.ass').is_file()


def test_convert_smi_files_preserves_existing_ass_outputs_by_default(tmp_path):
    source = tmp_path / 'episode.smi'
    existing = tmp_path / 'episode.kor.ass'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>First cue\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )
    existing.write_text('Keep this output', encoding='utf-8')

    summary = convert_smi_files([source], overwrite=False)

    assert summary.outputs == 0
    assert summary.existing == 1
    assert summary.failed == 0
    assert existing.read_text(encoding='utf-8') == 'Keep this output'
