from accumulator import accumulate

def test_independent_calls():
    assert accumulate(1) == [1]
    assert accumulate(2) == [2]
