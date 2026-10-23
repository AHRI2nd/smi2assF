"""Preserve subtitle text while excluding markup-only content."""
import pytest

from smi2ass import convert_smi


def caption(text):
    return '<SYNC Start=0><P Class=KRCC>' + text + '<SYNC Start=1000><P Class=KRCC>&nbsp;'


def dialogue_text(source):
    outputs, _ = convert_smi(source)
    return [line.split(',', 9)[9] for data in outputs.values()
            for line in data.decode().splitlines() if line.startswith('Dialogue:')]


@pytest.mark.parametrize('text', ['smi2ass_unicode(65)', 'smi2ass_unicode(32)'])
def test_original_placeholder_like_text_is_preserved(text):
    assert dialogue_text(caption(text)) == [text]


@pytest.mark.parametrize(('text', 'expected'), [
    ('&amp;lt;', '&lt;'), ('&amp;amp;', '&amp;'),
    ('A&nbsp;&nbsp;B', 'A\u00a0\u00a0B'),
    ('<b>A</b>   <i>B</i>', r'{\b1}A{\b0}   {\i1}B{\i0}'),
])
def test_entities_decode_once_and_spaces_survive(text, expected):
    assert dialogue_text(caption(text)) == [expected]


@pytest.mark.parametrize('comment', ['<!-- hidden -->', '<!-- <SYNC Start=500><P Class=KRCC>hidden -->',
                                   '<!--\n<SYNC Start=500>\nhidden\n-->'])
def test_comments_do_not_change_text_or_cue_boundaries(comment):
    outputs, diagnostics = convert_smi(caption('Before' + comment + 'After'))
    assert dialogue_text(caption('Before' + comment + 'After')) == ['BeforeAfter']
    assert b'0:00:00.00,0:00:01.00' in outputs['']
    assert len([d for d in diagnostics if d.code == 'SYNC_CLOSE_INSERTED']) == 1


def test_comment_lines_preserve_diagnostic_source_line_numbers():
    _, diagnostics = convert_smi('<!--\n<SYNC Start=99>\n-->\n<SYNC Start=bad><P>Skip')
    assert [d.line for d in diagnostics if d.code == 'INVALID_TIMESTAMP'] == [4]


@pytest.mark.parametrize('text', ['<b>&nbsp;</b>', '<font color=red> </font>', '<br>', '<i><!-- hidden --></i>'])
def test_markup_only_cues_do_not_generate_dialogues(text):
    outputs, _ = convert_smi(caption(text))
    assert outputs == {}


def test_styled_blank_still_ends_previous_caption():
    source = ('<SYNC Start=0><P Class=KRCC>Visible'
              '<SYNC Start=1000><P Class=KRCC><b>&nbsp;</b>'
              '<SYNC Start=2000><P Class=KRCC>&nbsp;')
    assert dialogue_text(source) == ['Visible']
    assert b'0:00:00.00,0:00:01.00' in convert_smi(source)[0]['']


def test_literal_ass_overrides_and_linebreaks_are_escaped():
    assert dialogue_text(caption(r'{\alpha&HFF&}Visible\NNext')) == [
        '\\{\\\u2060alpha&HFF&\\}Visible\\\u2060NNext']


def test_generated_style_and_break_commands_still_work():
    assert dialogue_text(caption('<b>A<br>B</b>')) == [r'{\b1}A\NB{\b0}']


@pytest.mark.parametrize('start', ['9' * 4500, '9' * 4500 + '??'], ids=['integer', 'suffix'])
def test_oversized_timestamps_are_skipped_with_diagnostic(start):
    outputs, diagnostics = convert_smi('<SYNC Start=' + start + '><P>Skip<SYNC Start=1><P>&nbsp;')
    assert outputs == {}
    assert any(d.code == 'INVALID_TIMESTAMP' and d.severity == 'skip' for d in diagnostics)


def test_excessive_nesting_returns_diagnostic_instead_of_crashing():
    outputs, diagnostics = convert_smi(caption('<b>' * 1100 + 'Text' + '</b>' * 1100))
    assert outputs == {}
    assert any(d.code == 'INPUT_NESTING_LIMIT' and d.severity == 'skip' for d in diagnostics)
