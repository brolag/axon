import pytest
from retry import retry

def test_succeeds_after_failures():
    calls = {'n': 0}
    def fn():
        calls['n'] += 1
        if calls['n'] < 3:
            raise ValueError('boom')
        return 'ok'
    assert retry(fn, 5) == 'ok'
    assert calls['n'] == 3

def test_reraises():
    def always_fail():
        raise KeyError('x')
    with pytest.raises(KeyError):
        retry(always_fail, 2)
