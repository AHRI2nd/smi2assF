def test_pytest_uses_python_level_output_capture(pytestconfig):
    assert pytestconfig.getoption('capture') == 'sys'
