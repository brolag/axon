import io
from contextlib import redirect_stdout
import payments

def _logs(fn, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()

def test_logs():
    assert 'CALL charge' in _logs(payments.charge, 10)
    assert 'CALL refund' in _logs(payments.refund, 5)
    assert 'CALL balance' in _logs(payments.balance, 1, 2)
