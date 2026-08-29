import pytest
from playwright_executor.parser import TestCaseParser

def test_parser_valid_steps():
    source = """
browser = open_browser()
navigate(browser, "https://example.com")
username = find_element(browser, "username")
fill(username, "tomsmith")
click(username)
wait(2000)
screenshot(browser, "test_pic")
close_browser(browser)
"""
    parser = TestCaseParser(source)
    steps = parser.parse()
    
    assert len(steps) == 8
    assert steps[0] == {"action": "open_browser", "variable": "browser"}
    assert steps[1] == {"action": "navigate", "browser": "browser", "url": "https://example.com"}
    assert steps[2] == {"action": "find_element", "browser": "browser", "locator": "username", "variable": "username"}
    assert steps[3] == {"action": "fill", "element": "username", "value": "tomsmith"}
    assert steps[4] == {"action": "click", "element": "username"}
    assert steps[5] == {"action": "wait", "duration": 2000}
    assert steps[6] == {"action": "screenshot", "browser": "browser", "name": "test_pic"}
    assert steps[7] == {"action": "close_browser", "browser": "browser"}

def test_parser_unsupported_action():
    source = "invalid_action(browser)"
    parser = TestCaseParser(source)
    with pytest.raises(ValueError, match="Unsupported action"):
        parser.parse()

def test_parser_invalid_arguments():
    # navigate with wrong number of arguments
    source = "navigate(browser)"
    parser = TestCaseParser(source)
    with pytest.raises(ValueError, match="navigate\\(browser, url\\) requires 2 arguments"):
        parser.parse()

def test_parser_invalid_string():
    # navigate with integer instead of string URL
    source = "navigate(browser, 123)"
    parser = TestCaseParser(source)
    with pytest.raises(ValueError, match="URL must be a string"):
        parser.parse()

def test_parser_invalid_number():
    # wait with string duration instead of number
    source = "wait('2000')"
    parser = TestCaseParser(source)
    with pytest.raises(ValueError, match="duration must be a number"):
        parser.parse()

def test_parser_negative_number():
    # wait with negative duration
    source = "wait(-100)"
    parser = TestCaseParser(source)
    with pytest.raises(ValueError, match="Expected constant value, got UnaryOp"):
        parser.parse()


def test_parser_unsupported_statement():
    source = """
for i in range(5):
    pass
"""
    parser = TestCaseParser(source)
    with pytest.raises(ValueError, match="Unsupported Python statement"):
        parser.parse()
