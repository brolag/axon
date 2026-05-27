import json
from formatter import format_output

def test_plain():
    assert format_output({'a': 1}) == 'a: 1'

def test_json():
    assert json.loads(format_output({'a': 1}, as_json=True)) == {'a': 1}
