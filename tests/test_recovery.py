import os
import subprocess
import sys

from smi2ass import convert_smi


def test_input_without_sync_cues_is_reported_as_unrecoverable():
    outputs, diagnostics = convert_smi('<SAMI><BODY>No cue</BODY></SAMI>')

    assert outputs == {}
    assert len(diagnostics) == 1
    assert diagnostics[0].code == 'NO_SYNC_CUES'
    assert diagnostics[0].severity == 'skip'


def test_missing_sync_closings_are_repaired_and_reported_with_source_lines():
    source = (
        '<SAMI>\n<BODY>\n'
        '<SYNC Start=0><P Class=KRCC>First\n'
        '<SYNC Start=1000><P Class=KRCC>Second\n'
        '<SYNC Start=2000><P Class=KRCC>&nbsp;\n'
        '</BODY></SAMI>'
    )

    outputs, diagnostics = convert_smi(source)

    repairs = [item for item in diagnostics if item.code == 'SYNC_CLOSE_INSERTED']
    assert [item.line for item in repairs] == [3, 4]
    output = outputs[''].decode('utf-8')
    assert 'Dialogue: 0,0:00:00.00,0:00:01.00,Default' in output
    assert 'Dialogue: 0,0:00:01.00,0:00:02.00,Default' in output


def test_unparseable_timestamp_skips_only_that_cue_without_reusing_previous_time():
    source = (
        '<SYNC Start=0><P Class=KRCC>Valid before\n'
        '<SYNC Start=unknown><P Class=KRCC>Must be skipped\n'
        '<SYNC Start=2000><P Class=KRCC>Valid after\n'
        '<SYNC Start=3000><P Class=KRCC>&nbsp;'
    )

    outputs, diagnostics = convert_smi(source)

    skipped = [item for item in diagnostics if item.code == 'INVALID_TIMESTAMP']
    assert len(skipped) == 1
    assert skipped[0].line == 2
    output = outputs[''].decode('utf-8')
    assert 'Must be skipped' not in output
    assert 'Valid before' in output
    assert 'Valid after' in output


def test_trailing_question_marks_on_integer_timestamp_are_salvaged():
    source = (
        '<SYNC Start=1000??><P Class=KRCC>Recovered time\n'
        '<SYNC Start=2000><P Class=KRCC>&nbsp;'
    )

    outputs, diagnostics = convert_smi(source)

    repairs = [item for item in diagnostics if item.code == 'TIMESTAMP_SUFFIX_REMOVED']
    assert len(repairs) == 1
    assert repairs[0].line == 1
    assert '1000' in repairs[0].message
    assert 'Recovered time' in outputs[''].decode('utf-8')


def test_unclosed_formatting_tag_is_closed_and_reported():
    source = (
        '<SYNC Start=0><P Class=KRCC><b>Bold text\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;'
    )

    outputs, diagnostics = convert_smi(source)

    repairs = [item for item in diagnostics if item.code == 'FORMAT_CLOSE_INSERTED']
    assert len(repairs) == 1
    assert repairs[0].line == 1
    assert '{\\b1}Bold text {\\b0}' in outputs[''].decode('utf-8')


def test_unmatched_sync_closing_tag_is_removed_and_reported():
    source = (
        '</SYNC>\n'
        '<SYNC Start=0><P Class=KRCC>Text\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;'
    )

    outputs, diagnostics = convert_smi(source)

    repairs = [item for item in diagnostics if item.code == 'SYNC_CLOSE_REMOVED']
    assert len(repairs) == 1
    assert repairs[0].line == 1
    assert 'Text' in outputs[''].decode('utf-8')


def test_unreadable_cue_is_reported_and_cli_continues_with_other_files(tmp_path):
    damaged = tmp_path / 'damaged.smi'
    valid = tmp_path / 'valid.smi'
    damaged.write_text(
        '<SYNC Start=bad><P Class=KRCC>Skip me\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )
    valid.write_text(
        '<SYNC Start=0><P Class=KRCC>Keep me\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )
    environment = os.environ.copy()
    environment['PYTHONPATH'] = os.pathsep.join(
        filter(None, [str(tmp_path.parent), str(os.path.dirname(os.path.dirname(__file__)))])
    )

    result = subprocess.run(
        [sys.executable, '-m', 'smi2ass', str(damaged), str(valid)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert 'damaged.smi:1' in result.stderr
    assert 'damaged.smi: repaired 1, skipped 1' in result.stderr
    assert 'skipped 1' in result.stderr
    assert 'Keep me' in (tmp_path / 'valid.kor.ass').read_text(encoding='utf-8')
