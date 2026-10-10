import pytest

from smi2ass import convert_smi, convert_smi_file


def dialogues(contents):
    return [line for line in contents.decode('utf-8').splitlines() if line.startswith('Dialogue:')]


@pytest.mark.parametrize('closing', ['</P>', ''])
@pytest.mark.parametrize('order', [('KRCC', 'ENCC'), ('ENCC', 'KRCC')])
def test_each_paragraph_in_same_sync_has_independent_language_and_formatting(closing, order):
    text = {'KRCC': '<b>한국어</b><br>둘째 줄', 'ENCC': '<i>English</i>'}
    source = '<SYNC Start=0>' + ''.join(f'<P Class={lang}>{text[lang]}{closing}' for lang in order)
    source += '<SYNC Start=1000>' + ''.join(f'<P Class={lang}>&nbsp;{closing}' for lang in order)
    outputs, _ = convert_smi(source)
    assert set(outputs) == {'kor', 'eng'}
    assert dialogues(outputs['kor']) == [
        'Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0000,0000,0000,,{\\b1}한국어{\\b0}\\N둘째 줄']
    assert dialogues(outputs['eng']) == [
        'Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0000,0000,0000,,{\\i1}English{\\i0}']


def test_unclosed_formatting_does_not_leak_into_next_language():
    outputs, diagnostics = convert_smi(
        '<SYNC Start=0><P Class=KRCC><b>한국어<P Class=ENCC>English'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;<P Class=ENCC>&nbsp;')
    assert set(outputs) == {'kor', 'eng'}
    assert '{\\b1}' in outputs['kor'].decode('utf-8')
    assert '{\\b1}' not in outputs['eng'].decode('utf-8')
    assert any(item.code == 'FORMAT_CLOSE_INSERTED' for item in diagnostics)


def test_sparse_language_is_not_merged_or_deleted():
    source = '<SYNC Start=0><P Class=ENCC>English</P><P Class=JPCC>日本語</P>'
    for index in range(1, 31):
        source += f'<SYNC Start={index * 1000}><P Class=KRCC>Korean {index}</P>'
    source += '<SYNC Start=31000><P Class=KRCC>&nbsp;</P><P Class=ENCC>&nbsp;</P><P Class=JPCC>&nbsp;</P>'
    outputs, _ = convert_smi(source)
    assert set(outputs) == {'kor', 'eng', 'jpn'}
    assert 'English' in outputs['eng'].decode('utf-8')
    assert '日本語' in outputs['jpn'].decode('utf-8')
    assert 'English' not in outputs['kor'].decode('utf-8')


def test_duplicate_timestamp_aliases_preserve_both_paragraphs():
    outputs, _ = convert_smi(
        '<SYNC Start=0><P Class=krcc>First</P><P Class=KOCC>Second</P>'
        '<P Class=encc>English</P><SYNC Start=1000>'
        '<P Class=KRCC>&nbsp;</P><P Class=ENCC>&nbsp;</P>')
    assert set(outputs) == {'kor', 'eng'}
    assert dialogues(outputs['kor']) == [
        'Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0000,0000,0000,,First\\NSecond']


def test_missing_language_at_other_sync_does_not_end_its_cue():
    outputs, _ = convert_smi(
        '<SYNC Start=0><P Class=ENCC>English</P>'
        '<SYNC Start=500><P Class=KRCC>한국어</P>'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;</P>'
        '<SYNC Start=2000><P Class=ENCC>&nbsp;</P>')
    assert '0:00:00.00,0:00:02.00' in outputs['eng'].decode('utf-8')


def test_unknown_language_filename_is_safe_and_does_not_collide(tmp_path):
    source = tmp_path / 'multi.smi'
    source.write_text(
        '<SYNC Start=0><P Class=ENCC>Known</P><P Class=eng>Unknown</P>'
        '<P Class="../custom">Custom</P><P>No class</P>'
        '<SYNC Start=1000><P Class=ENCC>&nbsp;</P><P Class=eng>&nbsp;</P>'
        '<P Class="../custom">&nbsp;</P><P>&nbsp;</P>', encoding='utf-8')
    result = convert_smi_file(source)
    assert len(result.outputs) == 4
    assert len({path.name.casefold() for path in result.outputs}) == 4
    assert all(path.parent == tmp_path for path in result.outputs)
    assert all('..' not in path.name for path in result.outputs)
    assert all(path.suffix == '.ass' for path in result.outputs)


def test_last_text_without_end_timestamp_is_reported():
    outputs, diagnostics = convert_smi('<SYNC Start=0><P Class=KRCC>No ending')
    assert outputs == {}
    assert any(item.code == 'MISSING_END_TIMESTAMP' and item.severity == 'skip' for item in diagnostics)
