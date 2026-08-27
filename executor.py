import ast
import json
import logging
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from object_repository import OBJECT_REPOSITORY


# ============================================================
# Directories Configuration


OUTPUT_DIR = Path("output")
LOG_DIR = Path("logs")
SCREENSHOT_DIR = Path("screenshots")
REPORT_DIR = Path("reports")

OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)


# ============================================================
# Logger setup
# ============================================================

logger = logging.getLogger("executor")

def setup_logging(test_case_name):
    """
    Configure logging for a test case.

    Logs are written to logs/{test_case_name}.log
    and displayed in the console.
    """
    log_file = LOG_DIR / f"{test_case_name}.log"

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove existing handlers
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    # File handler
    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8"
    )

    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
    )

    # Console handler
    stream_handler = logging.StreamHandler()

    stream_handler.setFormatter(
        logging.Formatter(
            "%(levelname)s - %(message)s"
        )
    )

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


# ============================================================
# Supported actions
# ============================================================

SUPPORTED_ACTIONS = {
    "open_browser",
    "navigate",
    "find_element",
    "click",
    "fill",
    "wait",
    "close_browser",
    "screenshot",
}


# ============================================================
# AST -> JSON
# ============================================================

class TestCaseParser:
    """
    Parses a Python test case using the AST module.
    The Python test case is never executed during this phase.
    """

    def __init__(self, source):
        self.source = source
        self.tree = ast.parse(source)
        self.steps = []
        self.temp_counter = 0

    def parse(self):
        """
        Convert the AST into a list of generic JSON steps.
        """
        for node in self.tree.body:
            self._parse_statement(node)
        return self.steps

    def _parse_statement(self, node):
        """
        Parse supported top-level Python statements.
        """
        # browser = open_browser()
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise ValueError("Only simple assignments are supported.")

            target = node.targets[0]
            if not isinstance(target, ast.Name):
                raise ValueError("Only variable assignments are supported.")

            variable_name = target.id

            if not isinstance(node.value, ast.Call):
                raise ValueError(
                    f"Unsupported assignment for variable '{variable_name}'."
                )

            self._parse_call(node.value, assigned_variable=variable_name)

        # click(username) / wait(1000) / navigate(browser, url) / screenshot(browser, "name")
        elif isinstance(node, ast.Expr):
            if not isinstance(node.value, ast.Call):
                raise ValueError("Only function calls are supported as expressions.")
            self._parse_call(node.value)

        # Ignore imports
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            return

        else:
            raise ValueError(f"Unsupported Python statement: {type(node).__name__}")

    def _parse_call(self, node, assigned_variable=None):
        """
        Convert a Python function call into a generic JSON step.
        """
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are supported.")

        action = node.func.id

        if action not in SUPPORTED_ACTIONS:
            raise ValueError(f"Unsupported action: {action}")

        # open_browser()
        if action == "open_browser":
            if node.args:
                raise ValueError("open_browser() does not accept arguments.")
            if assigned_variable is None:
                raise ValueError("open_browser() must be assigned to a variable.")

            self.steps.append({
                "action": "open_browser",
                "variable": assigned_variable,
            })

        # navigate(browser, url)
        elif action == "navigate":
            if len(node.args) != 2:
                raise ValueError("navigate(browser, url) requires 2 arguments.")

            browser = self._parse_name(node.args[0])
            url = self._parse_string(node.args[1], "URL")

            self.steps.append({
                "action": "navigate",
                "browser": browser,
                "url": url,
            })

        # find_element(browser, locator)
        elif action == "find_element":
            if len(node.args) != 2:
                raise ValueError("find_element(browser, locator) requires 2 arguments.")

            browser = self._parse_name(node.args[0])
            locator = self._parse_string(
                 node.args[1],
                 "locator"
            )

            if assigned_variable is None:
                assigned_variable = self._create_temp_variable()

            self.steps.append({
                "action": "find_element",
                "browser": browser,
                "locator": locator,
                "variable": assigned_variable,
            })

        # click(element)
        elif action == "click":
            if len(node.args) != 1:
                raise ValueError("click(element) requires 1 argument.")

            argument = node.args[0]

            # click(username)
            if isinstance(argument, ast.Name):
                self.steps.append({
                    "action": "click",
                    "element": argument.id,
                })

            # click(find_element(browser, "login"))
            elif isinstance(argument, ast.Call):
                temp_variable = self._create_temp_variable()
                self._parse_call(argument, assigned_variable=temp_variable)
                self.steps.append({
                    "action": "click",
                    "element": temp_variable,
                })
            else:
                raise ValueError("click() expects an element variable or element-returning call.")

        # fill(element, value)
        elif action == "fill":
            if len(node.args) != 2:
                raise ValueError("fill(element, value) requires 2 arguments.")

            element = self._parse_name(node.args[0])
            value = self._parse_constant(node.args[1])

            self.steps.append({
                "action": "fill",
                "element": element,
                "value": value,
            })

        # wait(duration)
        elif action == "wait":
            if len(node.args) != 1:
                raise ValueError("wait(duration) requires 1 argument.")

            duration = self._parse_number(
                node.args[0],
                "duration"
            )

            self.steps.append({
                "action": "wait",
                "duration": duration,
            })

        # screenshot(browser, name)
        elif action == "screenshot":
            if len(node.args) != 2:
                raise ValueError("screenshot(browser, name) requires 2 arguments.")

            browser = self._parse_name(node.args[0])
            name = self._parse_string(
               node.args[1],
               "screenshot name"
            )

            self.steps.append({
                "action": "screenshot",
                "browser": browser,
                "name": name,
            })

        # close_browser(browser)
        elif action == "close_browser":
            if len(node.args) != 1:
                raise ValueError("close_browser(browser) requires 1 argument.")

            browser = self._parse_name(node.args[0])

            self.steps.append({
                "action": "close_browser",
                "browser": browser,
            })

    def _parse_name(self, node):
        if not isinstance(node, ast.Name):
            raise ValueError(f"Expected variable name, got {type(node).__name__}")
        return node.id

    def _parse_constant(self, node):
        if not isinstance(node, ast.Constant):
            raise ValueError(f"Expected constant value, got {type(node).__name__}")
        return node.value

    def _create_temp_variable(self):
        self.temp_counter += 1
        return f"__element_{self.temp_counter}"
    
    def _parse_string(self, node, argument_name):
        value = self._parse_constant(node)

        if not isinstance(value, str):
            raise ValueError(
                f"{argument_name} must be a string."
            )

        return value


def _parse_number(self, node, argument_name):
    value = self._parse_constant(node)

    if not isinstance(value, (int, float)):
        raise ValueError(
            f"{argument_name} must be a number."
        )

    if value < 0:
        raise ValueError(
            f"{argument_name} must be greater than or equal to 0."
        )

    return value
# ============================================================
# JSON generation
# ============================================================

def generate_json(test_case_path):
    """
    Read a Python test case, parse it with AST,
    and generate the JSON representation.
    """
    test_case_name = Path(test_case_path).name.replace(".py", "")
    json_output_path = OUTPUT_DIR / f"{test_case_name}.json"

    logger.info("Reading test case: %s", test_case_path)
    source = Path(test_case_path).read_text(encoding="utf-8")

    logger.info("Parsing Python source using AST")
    parser = TestCaseParser(source)
    steps = parser.parse()

    test_case = {
        "name": test_case_name,
        "steps": steps,
    }

    json_output_path.write_text(
        json.dumps(test_case, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("JSON test case generated: %s", json_output_path)
    return test_case


# ============================================================
# Playwright Executor
# ============================================================

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
            self.generate_report()
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
        self.page.goto(url, wait_until="domcontentloaded")

    def find_element(self, step):
        logical_locator = step["locator"]

        if logical_locator not in OBJECT_REPOSITORY:
            raise ValueError(
                f"Locator '{logical_locator}' not found in Object Repository."
            )

        playwright_locator = OBJECT_REPOSITORY[logical_locator]
        logger.info("Resolving '%s' -> '%s'", logical_locator, playwright_locator)
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
        name = step["name"]
        screenshot_path = SCREENSHOT_DIR / f"{name}.png"
        logger.info("Saving screenshot: %s", screenshot_path)
        self.page.screenshot(path=str(screenshot_path))

    def close_browser(self, step):
        logger.info("Closing browser")
        if self.browser is not None:
            self.browser.close()
            self.browser = None

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

    def generate_report(self):
        """
        Generate execution report in HTML format.
        """
        test_name = self.test_case["name"]
        duration = (self.end_time - self.start_time) if (self.start_time and self.end_time) else 0.0
        
        total_steps = len(self.test_case["steps"])
        successful_steps = sum(1 for s in self.steps_stats if s["status"] == "PASSED")
        failed_steps = sum(1 for s in self.steps_stats if s["status"] == "FAILED")
        
        # Build steps rows for the HTML table
        table_rows = ""
        for s in self.steps_stats:
            err_cell = f"<td style='color: red;'>{s['error']}</td>" if s['error'] else "<td>-</td>"
            status_color = "green" if s['status'] == "PASSED" else "red"
            table_rows += f"""
            <tr>
                <td>{s['step']}</td>
                <td>{s['action']}</td>
                <td style='color: {status_color}; font-weight: bold;'>{s['status']}</td>
                <td>{s['duration']:.3f}s</td>
                {err_cell}
            </tr>
            """
            
        # In case we have unexecuted steps due to failure, fill them in the report table
        executed_count = len(self.steps_stats)
        if executed_count < total_steps:
            for index in range(executed_count + 1, total_steps + 1):
                step = self.test_case["steps"][index - 1]
                table_rows += f"""
                <tr style='color: #888;'>
                    <td>{index}</td>
                    <td>{step['action']}</td>
                    <td>NOT RUN</td>
                    <td>-</td>
                    <td>-</td>
                </tr>
                """

        # Generate separate reports/test_case_report.html
        report_file = REPORT_DIR / f"{test_name}_report.html"
        
        error_section = ""
        if self.status == "FAILED":
            error_section = f"""
            <div class="error-box">
                <strong>Failed Action:</strong> {self.failed_action}<br>
                <strong>Error Details:</strong> {self.error_message}
            </div>
            """

        status_class = f"status-{self.status.lower()}"
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Test Execution Report - {test_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            background-color: #f8f9fa;
            color: #333;
        }}
        h1 {{
            color: #0056b3;
            border-bottom: 2px solid #0056b3;
            padding-bottom: 10px;
        }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 30px;
        }}
        .metric {{
            margin-bottom: 12px;
            font-size: 16px;
        }}
        .label {{
            font-weight: bold;
            width: 220px;
            display: inline-block;
        }}
        .status-passed {{
            color: #28a745;
            font-weight: bold;
            background: #d4edda;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .status-failed {{
            color: #dc3545;
            font-weight: bold;
            background: #f8d7da;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .error-box {{
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
            font-family: monospace;
            white-space: pre-wrap;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background-color: #0056b3;
            color: white;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        tr:nth-child(even) {{
            background-color: #f1f3f5;
        }}
    </style>
</head>
<body>
    <h1>Test Case: {test_name}</h1>
    <div class="summary">
        <div class="metric"><span class="label">Status:</span> <span class="{status_class}">{self.status}</span></div>
        <div class="metric"><span class="label">Total steps:</span> {total_steps}</div>
        <div class="metric"><span class="label">Successful steps:</span> {successful_steps}</div>
        <div class="metric"><span class="label">Failed steps:</span> {failed_steps}</div>
        <div class="metric"><span class="label">Execution duration:</span> {duration:.2f} seconds</div>
        {error_section}
    </div>

    <h2>Steps Execution Details</h2>
    <table>
        <thead>
            <tr>
                <th>Step</th>
                <th>Action</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Error Details</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
</body>
</html>
"""
        report_file.write_text(html_content, encoding="utf-8")
        logger.info("HTML report generated: %s", report_file)


# ============================================================
# Main
# ============================================================

def main():
    if len(sys.argv) != 2:
        print("Usage: python executor.py tests/test_case.py")
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