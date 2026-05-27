from shapes import square_label, rect_label, circle_label

def test_labels():
    assert square_label(2) == 'area=4.00'
    assert rect_label(2, 3) == 'area=6.00'
    assert circle_label(1) == 'area=3.14'
