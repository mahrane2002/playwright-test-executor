from playwright_executor.parser import generate_json
from playwright_executor.executor import PlaywrightExecutor
from playwright_executor.logger import setup_logging

def test_navigation_functional():
    setup_logging("test_navigation")
    test_case = generate_json("test_cases/navigation.py")
    executor = PlaywrightExecutor(test_case)
    executor.execute()
    assert executor.status == "PASSED"
