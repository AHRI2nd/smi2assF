import os
import subprocess
import sys


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
