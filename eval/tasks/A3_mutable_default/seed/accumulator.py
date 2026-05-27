def accumulate(x, lst=[]):  # BUG: shared mutable default
    lst.append(x)
    return lst
