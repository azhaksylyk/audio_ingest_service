import pytest
from app.services.utils import parse_content_range

def test_parse():
    s,e,t = parse_content_range("bytes 0-9/10")
    assert (s,e,t)==(0,9,10)

def test_bad():
    with pytest.raises(ValueError):
        parse_content_range("0-9/10")