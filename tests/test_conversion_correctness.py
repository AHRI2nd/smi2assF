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
