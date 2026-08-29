import pytest
from app.calculator import add, subtract, multiply, divide, power, is_even

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_subtract():
    assert subtract(5, 3) == 2

def test_multiply():
    assert multiply(3, 4) == 12

def test_divide():
    assert divide(10, 2) == 5

def test_divide_by_zero():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)

def test_power():
    assert power(2, 3) == 8

def test_is_even():
    assert is_even(4) is True
    assert is_even(3) is False
