from billing.tax import calculate_tax

def test_tax():
    # fixture assumes 0.13 rate
    assert calculate_tax(100) == 13.0
