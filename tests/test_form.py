from playwright_executor.parser import generate_json
from playwright_executor.executor import PlaywrightExecutor
from playwright_executor.logger import setup_logging

def test_form_functional():
    setup_logging("test_form")
    test_case = generate_json("test_cases/form.py")
    executor = PlaywrightExecutor(test_case)
    executor.execute()
    assert executor.status == "PASSED"
