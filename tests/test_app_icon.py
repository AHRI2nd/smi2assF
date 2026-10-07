import struct
from pathlib import Path


ASSETS = Path(__file__).resolve().parents[1] / 'assets'


def test_windows_app_icon_contains_multiple_sizes():
    data = (ASSETS / 'smi2ass.ico').read_bytes()
    reserved, image_type, count = struct.unpack_from('<HHH', data)

    assert reserved == 0
    assert image_type == 1
    assert count >= 5
    dimensions = {
        (entry[0] or 256, entry[1] or 256)
        for entry in struct.iter_unpack('<BBBBHHII', data[6:6 + 16 * count])
    }
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= dimensions


def test_macos_app_icon_has_valid_icns_container():
    data = (ASSETS / 'smi2ass.icns').read_bytes()

    assert data[:4] == b'icns'
    assert struct.unpack_from('>I', data, 4)[0] == len(data)
