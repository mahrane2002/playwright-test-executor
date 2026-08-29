import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

from playwright_executor.logger import logger, setup_logging
from playwright_executor.object_repository import OBJECT_REPOSITORY
from playwright_executor.reporter import HTMLReporter
from playwright_executor.parser import generate_json

SCREENSHOT_DIR = Path("screenshots")

class PlaywrightExecutor:
    """
    Executes the generic JSON test case using Playwright.
    """

    def __init__(self, test_case):
        self.test_case = test_case
        self.variables = {}
        self.playwright = None
        self.browser = None
        self.page = None
        
        # Statistics tracking
        self.steps_stats = []
        self.start_time = None
        self.end_time = None
        self.status = "PASSED"
        self.error_message = None
        self.failed_action = None

    def execute(self):
        """
        Execute all JSON steps sequentially.
        """
        test_name = self.test_case["name"]
        logger.info("Starting test case: %s", test_name)
        self.start_time = time.time()

        try:
            self.playwright = sync_playwright().start()

            for index, step in enumerate(self.test_case["steps"], start=1):
                action = step["action"]
                logger.info("Executing step %s: %s", index, action)
                
                step_start = time.time()
                try:
                    self.execute_step(step)
                    step_duration = time.time() - step_start
                    self.steps_stats.append({
                        "step": index,
                        "action": action,
                        "status": "PASSED",
                        "duration": step_duration,
                        "error": None
                    })
                    logger.info("Step %s completed successfully", index)

                except Exception as exc:
                    step_duration = time.time() - step_start
                    self.status = "FAILED"
                    self.error_message = str(exc)
                    self.failed_action = action
                    self.steps_stats.append({
                        "step": index,
                        "action": action,
                        "status": "FAILED",
                        "duration": step_duration,
                        "error": str(exc)
                    })
                    logger.error("Step %s failed", index)
                    logger.error("Action: %s", action)
                    logger.error("Reason: %s", exc)
                    raise

        except Exception as exc:
            logger.exception("Test case failed: %s", test_name)
            self.status = "FAILED"
            if not self.error_message:
                self.error_message = str(exc)
            raise
        finally:
            self.end_time = time.time()
            self.cleanup()
            
            # Generate report
            reporter = HTMLReporter(
                test_case=self.test_case,
                status=self.status,
                steps_stats=self.steps_stats,
                start_time=self.start_time,
                end_time=self.end_time,
                error_message=self.error_message,
                failed_action=self.failed_action
            )
            reporter.generate()
            logger.info("Test case finished: %s", test_name)

    def execute_step(self, step):
        """
        Dispatch a JSON step to the appropriate Playwright operation.
        """
        action = step["action"]

        if action == "open_browser":
            self.open_browser(step)
        elif action == "navigate":
            self.navigate(step)
        elif action == "find_element":
            self.find_element(step)
        elif action == "click":
            self.click(step)
        elif action == "fill":
            self.fill(step)
        elif action == "wait":
            self.wait(step)
        elif action == "screenshot":
            self.screenshot(step)
        elif action == "close_browser":
            self.close_browser(step)
        else:
            raise ValueError(f"Unsupported execution action: {action}")

    def open_browser(self, step):
        self.browser = self.playwright.chromium.launch(headless=False)
        self.page = self.browser.new_page()
        variable = step["variable"]
        self.variables[variable] = self.browser
        logger.info("Browser opened and stored as '%s'", variable)

    def navigate(self, step):
        url = step["url"]
        logger.info("Navigating to %s", url)

        if self.browser is None:
            raise RuntimeError("Cannot navigate: browser is not open.")

        self.page.goto(url, wait_until="domcontentloaded")

    def find_element(self, step):
        if self.page is None:
            raise RuntimeError("Cannot find element: browser is not open.")

        logical_locator = step["locator"]

        if logical_locator not in OBJECT_REPOSITORY:
            raise ValueError(
                f"Locator '{logical_locator}' not found in Object Repository."
            )

        playwright_locator = OBJECT_REPOSITORY[logical_locator]

        logger.info(
            "Resolving '%s' -> '%s'",
            logical_locator,
            playwright_locator
        )

        element = self.page.locator(playwright_locator)
        variable = step["variable"]
        self.variables[variable] = element

    def click(self, step):
        element_name = step["element"]
        element = self._get_variable(element_name)
        logger.info("Clicking element '%s'", element_name)
        element.click()

    def fill(self, step):
        element_name = step["element"]
        value = step["value"]
        element = self._get_variable(element_name)
        logger.info("Filling element '%s' with '%s'", element_name, value)
        element.fill(str(value))

    def wait(self, step):
        duration = step["duration"]
        logger.info("Waiting %s ms", duration)
        self.page.wait_for_timeout(duration)

    def screenshot(self, step):
        if self.page is None:
            raise RuntimeError("Cannot take screenshot: browser is not open.")

        name = step["name"]
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        screenshot_path = SCREENSHOT_DIR / f"{name}.png"

        logger.info("Saving screenshot: %s", screenshot_path)
        self.page.screenshot(path=str(screenshot_path))

    def close_browser(self, step):
        logger.info("Closing browser")
        if self.browser is not None:
            self.browser.close()
            self.browser = None
            self.page = None

    def _get_variable(self, variable_name):
        if variable_name not in self.variables:
            raise ValueError(f"Runtime variable '{variable_name}' does not exist.")
        return self.variables[variable_name]

    def cleanup(self):
        if self.browser is not None:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None

        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m playwright_executor.executor test_cases/login.py")
        sys.exit(1)

    test_case_path = sys.argv[1]
    test_case_name = Path(test_case_path).name.replace(".py", "")

    setup_logging(test_case_name)

    try:
        # Phase 1: Python -> AST -> JSON
        test_case = generate_json(test_case_path)

        # Phase 2: JSON -> Playwright
        executor = PlaywrightExecutor(test_case)
        executor.execute()

    except Exception as exc:
        logger.error("Execution stopped: %s", exc)
        sys.exit(1)

if __name__ == "__main__":
    main()
