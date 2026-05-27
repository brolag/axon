from store import load, total

def test_store():
    assert load() == [1, 2, 3]
    assert total() == 6
