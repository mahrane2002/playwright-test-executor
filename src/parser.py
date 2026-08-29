import ast
import json
from pathlib import Path
from playwright_executor.logger import logger

OUTPUT_DIR = Path("output")

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

class TestCaseParser:
    """
    Parses a Python test case using the AST module.
    The Python test case is never executed during this phase.
    """
    __test__ = False

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

def generate_json(test_case_path):
    """
    Read a Python test case, parse it with AST,
    and generate the JSON representation.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
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
