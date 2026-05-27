def get_page(items, page, size):
    # page is 1-indexed
    start = page * size  # BUG: off by one, should be (page-1)*size
    return items[start:start + size]
