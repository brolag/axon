from counter import count

def test_count():
    assert count(['a', 'b', 'a']) == {'a': 2, 'b': 1}
