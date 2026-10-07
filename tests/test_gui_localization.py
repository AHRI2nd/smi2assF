from smi2ass_gui_support import detect_ui_language, localized_text


def test_detect_ui_language_uses_korean_device_locale():
    assert detect_ui_language('ko_KR.UTF-8') == 'ko'


def test_detect_ui_language_uses_english_for_other_device_locales():
    assert detect_ui_language('en_US.UTF-8') == 'en'
    assert detect_ui_language('ja_JP.UTF-8') == 'en'


def test_localized_text_uses_korean_or_english_copy():
    assert localized_text('drop_hint', 'ko') == '여기에 SMI 파일 또는 폴더를 놓으세요'
    assert localized_text('drop_hint', 'en') == 'Drop SMI files or folders here'
