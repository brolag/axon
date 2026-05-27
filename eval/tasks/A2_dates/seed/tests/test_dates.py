from dates import parse_date
from datetime import date

def test_valid():
    assert parse_date('2026-05-27') == date(2026, 5, 27)

def test_empty_returns_none():
    assert parse_date('') is None
