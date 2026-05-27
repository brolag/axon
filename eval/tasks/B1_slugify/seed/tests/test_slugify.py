from slugify import slugify

def test_basic():
    assert slugify('Hello World') == 'hello-world'

def test_collapse():
    assert slugify('  A--B  c ') == 'a-b-c'
