from playwright_executor.parser import generate_json
from playwright_executor.executor import PlaywrightExecutor
from playwright_executor.logger import setup_logging

def test_screenshot_functional():
    setup_logging("test_screenshot")
    test_case = generate_json("test_cases/screenshot.py")
    executor = PlaywrightExecutor(test_case)
    executor.execute()
    assert executor.status == "PASSED"
