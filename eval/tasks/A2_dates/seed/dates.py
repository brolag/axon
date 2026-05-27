from datetime import date

def parse_date(s):
    y, m, d = s.split('-')  # BUG: ValueError on ''
    return date(int(y), int(m), int(d))
