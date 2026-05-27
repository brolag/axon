def square_label(s):
    a = s * s
    return f'area={a:.2f}'

def rect_label(w, h):
    a = w * h
    return f'area={a:.2f}'

def circle_label(r):
    a = 3.14159 * r * r
    return f'area={a:.2f}'
