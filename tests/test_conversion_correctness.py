import os
import subprocess
import sys

import pytest

from smi2ass import convert_smi, ms2timecode


@pytest.mark.parametrize(
    ('color', 'ass_color'),
    [
        ('#123456', '563412'),
        ('#808080', '808080'),
        ('#C0C0C0', 'c0c0c0'),
        ('red', '0000ff'),
    ],
)
def test_rgb_colors_convert_to_ass_bgr(color, ass_color):
    source = (
        '<SYNC Start=0><P Class=KRCC>'
        '<font color="%s">Tint</font>' % color
        + '<SYNC Start=1000><P Class=KRCC>&nbsp;'
    )

    outputs, _ = convert_smi(source)

    assert ('{\\c&H%s&}Tint{\\c}' % ass_color) in outputs[''].decode('utf-8')


def test_invalid_color_value_is_not_partially_interpreted():
    source = (
        '<SYNC Start=0><P Class=KRCC>'
        '<font color="#badbadbad">Keep text</font>'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;'
    )

    outputs, diagnostics = convert_smi(source)
    output = outputs[''].decode('utf-8')

    assert 'Keep text' in output
    assert '{\\c&H' not in output
    assert any(item.code == 'UNKNOWN_COLOR' for item in diagnostics)


@pytest.mark.parametrize(
    ('milliseconds', 'expected'),
    [
        (1995, '0:00:02.00'),
        (59995, '0:01:00.00'),
        (3599995, '1:00:00.00'),
    ],
)
def test_centisecond_rounding_carries_into_larger_time_units(milliseconds, expected):
    assert ms2timecode(milliseconds) == expected


def test_extensionless_input_uses_its_filename_stem_in_dotted_parent(tmp_path):
    project_root = os.path.dirname(os.path.dirname(__file__))
    input_directory = tmp_path / 'directory.with.dots'
    input_directory.mkdir()
    source = input_directory / 'subtitle'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>Caption\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )
    environment = os.environ.copy()
    environment['PYTHONPATH'] = project_root

    result = subprocess.run(
        [sys.executable, '-m', 'smi2ass', str(source)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (input_directory / 'subtitle.kor.ass').exists()
    assert not (tmp_path / 'directory.kor.ass').exists()


def formatted_caption(text):
    outputs, _ = convert_smi('<SYNC Start=0><P Class=KRCC>' + text + '<SYNC Start=1000><P Class=KRCC>&nbsp;')
    return outputs[''].decode('utf-8')


def test_bold_preserves_nested_italic():
    assert r'{\b1}A{\i1}B{\i0}C{\b0}' in formatted_caption('<b>A<i>B</i>C</b>')


def test_nested_font_restores_outer_color():
    assert r'{\c&H0000ff&}A{\c&Hff0000&}B{\c&H0000ff&}C{\c}' in formatted_caption('<font color=red>A<font color=blue>B</font>C</font>')


def test_nested_same_style_restores_parent():
    assert r'{\b1}A{\b1}B{\b1}C{\b0}' in formatted_caption('<b>A<b>B</b>C</b>')


def test_nested_underline_strike_break_and_ruby():
    assert r'{\u1}{\s1}A\NB{\s0}{\fscx50}{\fscy50}' in formatted_caption('<u><s>A<br>B</s><rt><i>R</i></rt></u>')
    assert r'{\i1}R{\i0}' in formatted_caption('<u><s>A<br>B</s><rt><i>R</i></rt></u>')
