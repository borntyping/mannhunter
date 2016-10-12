import pytest

import psutil


def test_mannhunter(mannhunter):
    assert mannhunter


@pytest.mark.parametrize('name,value,expected', [
    ('percentage', '50%', psutil.virtual_memory().total / 2),
    ('1gb', '1gb', 1024 * 1024 * 1024),
    ('1mb', '1mb', 1024 * 1024),
    ('1kb', '1kb', 1024),
    ('bytes', '1024', 1024),
])
def test_limit(mannhunter, name, value, expected):
    mannhunter.add_program(name=name, memory=value)
    assert mannhunter.limit(name) == expected


def test_limit_above_zero(mannhunter):
    with pytest.raises(RuntimeError):
        mannhunter.add_program(name='invalid', memory='0%')


def test_default_limit(mannhunter):
    assert mannhunter.limit('unknown') == mannhunter.default_limit
