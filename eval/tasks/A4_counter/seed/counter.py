def count(items):
    counts = {}
    for it in items:
        counts[it] += 1  # BUG: KeyError on first sight
    return counts
