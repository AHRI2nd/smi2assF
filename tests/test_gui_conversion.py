from smi2ass_gui_support import convert_smi_files
import pytest


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


@pytest.mark.parametrize('source_text', [
    '<SAMI><BODY>No cue</BODY></SAMI>',
    '<SYNC Start=0><P Class=KRCC>&nbsp;<SYNC Start=1000><P Class=KRCC>&nbsp;',
    '<SYNC Start=0><P Class=KRCC>No ending',
])
def test_no_output_is_counted_as_one_problem_file(tmp_path, source_text):
    source = tmp_path / 'empty.smi'
    source.write_text(source_text, encoding='utf-8')
    summary = convert_smi_files([source])
    assert summary.total == 1
    assert summary.outputs == summary.existing == 0
    assert summary.failed == 1


def test_partial_conversion_counts_one_problem_file_despite_multiple_skips(tmp_path):
    source = tmp_path / 'partial.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC>Keep'
                      '<SYNC Start=bad><P Class=KRCC>Skip one'
                      '<SYNC Start=bad><P Class=KRCC>Skip two'
                      '<SYNC Start=1000><P Class=KRCC>&nbsp;', encoding='utf-8')
    summary = convert_smi_files([source])
    assert summary.outputs == 1
    assert summary.failed == 1
    assert 'Keep' in (tmp_path / 'partial.kor.ass').read_text(encoding='utf-8')


def test_repair_and_color_warning_with_output_are_not_failures(tmp_path):
    source = tmp_path / 'warning.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC><font color="not-a-color">Keep</font>'
                      '<SYNC Start=1000><P Class=KRCC>&nbsp;', encoding='utf-8')
    summary = convert_smi_files([source])
    assert summary.outputs == 1 and summary.failed == 0


def test_subcentisecond_transition_is_reported_as_a_warning_not_a_failure(tmp_path):
    source = tmp_path / 'karaoke.smi'
    source.write_text(
        '<SYNC Start=1345><P Class=KRCC><font color="red">EARLY</font>'
        '<SYNC Start=1349><P Class=KRCC><font color="blue">LATEST</font>'
        '<SYNC Start=2000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )

    summary = convert_smi_files([source])

    assert summary.outputs == 1
    assert summary.warnings == 1
    assert summary.failed == 0


def test_unreadable_input_does_not_stop_other_files(tmp_path):
    source = tmp_path / 'good.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC>Keep<SYNC Start=1000><P Class=KRCC>&nbsp;', encoding='utf-8')
    summary = convert_smi_files([tmp_path / 'missing.smi', source])
    assert (summary.total, summary.outputs, summary.failed) == (2, 1, 1)


def test_output_write_failure_is_counted(tmp_path, monkeypatch):
    import smi2ass
    from pathlib import Path
    original = smi2ass.publish_ass
    def publish(dst, contents, overwrite):
        if Path(dst).suffix == '.ass':
            raise PermissionError('read-only output')
        return original(dst, contents, overwrite)
    source = tmp_path / 'source.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC>Keep<SYNC Start=1000><P Class=KRCC>&nbsp;', encoding='utf-8')
    monkeypatch.setattr(smi2ass, 'publish_ass', publish)
    summary = convert_smi_files([source])
    assert summary.outputs == 0 and summary.failed == 1


def test_later_language_write_failure_preserves_successful_output_count(tmp_path, monkeypatch):
    import smi2ass
    from pathlib import Path
    original = smi2ass.publish_ass
    def publish(dst, contents, overwrite):
        if Path(dst).name == 'multi.eng.ass':
            raise PermissionError('English output unavailable')
        return original(dst, contents, overwrite)
    source = tmp_path / 'multi.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC>한국어</P><P Class=ENCC>English</P>'
                      '<SYNC Start=1000><P Class=KRCC>&nbsp;</P><P Class=ENCC>&nbsp;</P>', encoding='utf-8')
    monkeypatch.setattr(smi2ass, 'publish_ass', publish)
    summary = convert_smi_files([source])
    assert summary.outputs == 1
    assert summary.failed == 1
    assert (tmp_path / 'multi.kor.ass').is_file()
