from src.add import add
from src.classes import Person


def test_add():
    assert add(1, 2) == 3


def test_greet():
    p = Person("John")
    assert p.greet() == "Hello, John"
