import os
import subprocess
import sys

import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def run_cli(*arguments, cwd, env=None):
    environment = os.environ.copy()
    environment['PYTHONPATH'] = PROJECT_ROOT
    if env:
        environment.update(env)
    return subprocess.run(
        [sys.executable, '-m', 'smi2ass', *map(str, arguments)],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
    )


def test_utf16_sami_input_is_detected_and_written_as_utf8_ass(tmp_path):
    source = tmp_path / 'korean.smi'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>안녕하세요\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-16',
    )

    result = run_cli(source, cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    output = (tmp_path / 'korean.kor.ass').read_bytes()
    assert '안녕하세요' in output.decode('utf-8')


def test_multiple_language_input_writes_separate_ass_files(tmp_path):
    source = tmp_path / 'multi.smi'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>한국어\n'
        '<SYNC Start=0><P Class=ENCC>English\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;\n'
        '<SYNC Start=1000><P Class=ENCC>&nbsp;',
        encoding='utf-8',
    )

    result = run_cli(source, cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert '한국어' in (tmp_path / 'multi.kor.ass').read_text(encoding='utf-8')
    assert 'English' in (tmp_path / 'multi.eng.ass').read_text(encoding='utf-8')


def test_cli_requires_at_least_one_input_file(tmp_path):
    result = run_cli(cwd=tmp_path)

    assert result.returncode == 2
    assert 'usage:' in result.stderr


def test_all_blank_input_fails_cli_and_gui(tmp_path):
    from smi2ass_gui_support import convert_smi_files
    source = tmp_path / 'blank.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC>&nbsp;<SYNC Start=1000><P Class=KRCC>&nbsp;')
    assert convert_smi_files([source]).failed == 1
    result = run_cli(source, cwd=tmp_path)
    assert result.returncode == 1


def test_subcentisecond_state_is_nonfatal_cli(tmp_path):
    source = tmp_path / 'partial.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC>Too short<SYNC Start=1><P Class=KRCC>Keep<SYNC Start=1000><P Class=KRCC>&nbsp;')
    result = run_cli(source, cwd=tmp_path)
    assert result.returncode == 0
    assert '[warning]' in result.stderr
    assert 'skipped 0' in result.stderr
    assert 'Keep' in (tmp_path / 'partial.kor.ass').read_text()


def test_cli_batch_output_collision_preserves_first_input(tmp_path):
    first = tmp_path / 'episode.smi'
    second = tmp_path / 'episode.txt'
    for source, caption in ((first, 'FIRST'), (second, 'SECOND')):
        source.write_text('<SYNC Start=0><P Class=KRCC>%s<SYNC Start=1000><P Class=KRCC>&nbsp;' % caption)
    result = run_cli(first, second, cwd=tmp_path)
    assert result.returncode == 1
    assert 'Competing output' in result.stderr
    output = (tmp_path / 'episode.kor.ass').read_text()
    assert 'FIRST' in output and 'SECOND' not in output
@pytest.mark.parametrize('body', [
    '<SYNC Start=' + '9' * 4500 + '><P>Bad<SYNC Start=1><P>&nbsp;',
    '<SYNC Start=0><P>' + '<b>' * 1100 + 'Bad' + '</b>' * 1100 + '<SYNC Start=1000><P>&nbsp;',
], ids=['oversized-timestamp', 'excessive-nesting'])
def test_cli_continues_after_parser_limit_error(tmp_path, body):
    from smi2ass import main
    damaged = tmp_path / 'damaged.smi'
    valid = tmp_path / 'valid.smi'
    damaged.write_text(body, encoding='utf-8')
    valid.write_text('<SYNC Start=0><P>Good<SYNC Start=1000><P>&nbsp;', encoding='utf-8')
    assert main([str(damaged), str(valid)]) == 1
    assert 'Good' in (tmp_path / 'valid.kor.ass').read_text()
