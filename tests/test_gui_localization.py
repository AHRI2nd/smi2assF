from smi2ass_gui_support import detect_ui_language, localized_text


def test_detect_ui_language_uses_korean_device_locale():
    assert detect_ui_language('ko_KR.UTF-8') == 'ko'


def test_detect_ui_language_uses_english_for_other_device_locales():
    assert detect_ui_language('en_US.UTF-8') == 'en'
    assert detect_ui_language('ja_JP.UTF-8') == 'en'


def test_localized_text_uses_korean_or_english_copy():
    assert localized_text('drop_hint', 'ko') == '.smi 파일을 여기에 놓으세요'
    assert localized_text('drop_hint', 'en') == 'Drop .smi files here'


def test_gui_result_copy_preserves_all_five_counts():
    for language in ('ko', 'en'):
        result = localized_text('result_summary', language, total=12, outputs=34,
                                existing=56, failed=78, scan_errors=90)
        for count in ('12', '34', '56', '78', '90'):
            assert count in result
        assert len(result.splitlines()) == 3
