from smi2ass import smi2ass


def test_simple_sami_converts_to_default_language_ass():
    source = (
        '<SAMI><BODY>'
        '<SYNC Start=0><P Class=KRCC>Hello &amp; goodbye'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;'
        '</BODY></SAMI>'
    )

    result = smi2ass(source)

    assert list(result) == ['']
    output = result[''].decode('utf-8')
    assert 'Dialogue: 0,0:00:00.00,0:00:01.00,Default' in output
    assert 'Hello & goodbye' in output
