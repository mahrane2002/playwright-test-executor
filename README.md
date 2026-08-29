# Playwright Test Executor

A lightweight Python-based test execution framework that converts high-level Python test cases into a generic intermediate representation and executes them using [Playwright](https://playwright.dev/).

The project is designed to provide a simple and extensible approach to browser test automation while separating **test definition**, **test parsing**, **test execution**, **logging**, and **report generation**.

---

## Table of Contents

* [Overview](#overview)
* [Key Features](#key-features)
* [Architecture](#architecture)
* [Project Structure](#project-structure)
* [How It Works](#how-it-works)
* [Supported Actions](#supported-actions)
* [Writing Test Cases](#writing-test-cases)
* [Installation](#installation)
* [Running a Test Case](#running-a-test-case)
* [Generated Artifacts](#generated-artifacts)
* [Execution Reports](#execution-reports)
* [Logging](#logging)
* [Object Repository](#object-repository)
* [Testing](#testing)
* [Error Handling](#error-handling)
* [Design Principles](#design-principles)
* [Current Limitations](#current-limitations)
* [Extending the Framework](#extending-the-framework)
* [Development Workflow](#development-workflow)
* [Troubleshooting](#troubleshooting)
* [Future Improvements](#future-improvements)
* [License](#license)

---

# Overview

**Playwright Test Executor** is a small test automation framework built in Python.

Instead of executing test case Python files directly, the framework first analyzes them using Python's **Abstract Syntax Tree (AST)** module.

The test case is transformed into a generic JSON representation and is then executed by a dedicated Playwright executor.

The main execution pipeline is:

```text
Python Test Case
       │
       ▼
   AST Parser
       │
       ▼
 Generic JSON
       │
       ▼
Playwright Executor
       │
       ├──────────────► Logs
       │
       ├──────────────► Screenshots
       │
       └──────────────► HTML Report
```

This separation makes the framework easier to understand, test, maintain, and extend.

---

# Key Features

## Python-based test definition

Test cases are written using a small set of predefined functions such as:

* `open_browser()`
* `navigate()`
* `find_element()`
* `click()`
* `fill()`
* `wait()`
* `screenshot()`
* `close_browser()`

The functions form a lightweight test-case DSL (Domain-Specific Language).

The functions themselves do not perform browser automation. They define the vocabulary understood by the parser.

---

## AST-based parsing

The framework uses Python's built-in `ast` module to analyze test case source code.

The parser:

1. Reads the Python source file.
2. Builds an Abstract Syntax Tree.
3. Validates supported statements and arguments.
4. Extracts test actions.
5. Converts them into a generic JSON structure.
6. Saves the generated JSON under `output/`.

The test case Python code is therefore **parsed rather than executed during the parsing phase**.

---

## Playwright execution

The executor converts the generic actions into actual Playwright operations.

Supported browser operations currently include:

* Chromium browser launch
* Page navigation
* Element lookup
* Clicking
* Filling input fields
* Waiting
* Screenshots
* Browser closing

The executor also records execution statistics for every step.

---

## Object Repository

Logical element names are separated from their actual Playwright selectors.

For example:

```text
username
password
login
email
retrieve_password
```

are mapped to Playwright selectors in the Object Repository.

This allows selectors to be maintained independently from test cases.

---

## HTML execution reports

After every execution, an HTML report is generated.

The report contains:

* Overall test status
* Number of steps
* Successful steps
* Failed steps
* Execution duration
* Failed action
* Error details
* Per-step execution status
* Per-step duration
* Unexecuted steps

Dynamic values are HTML-escaped before being inserted into the report.

---

## Logging

The framework produces both:

* Console logs
* File logs

Logs are stored under:

```text
logs/
```

Each test case receives its own log file.

---

# Architecture

The framework is divided into several logical components.

```text
┌──────────────────────────────┐
│        Test Case DSL         │
│      test_cases/*.py         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│          AST Parser          │
│         parser.py            │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       Generic JSON IR        │
│          output/*.json       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│     Playwright Executor      │
│         executor.py          │
└───────┬──────────┬───────────┘
        │          │
        ▼          ▼
   ┌────────┐  ┌─────────────┐
   │ Logger │  │ Object Repo  │
   └────────┘  └─────────────┘
        │
        ▼
┌──────────────────────────────┐
│       Execution Results      │
├──────────────┬───────────────┤
│    Reports   │  Screenshots  │
└──────────────┴───────────────┘
```

---

# How It Works

The framework follows a two-phase execution model.

## Phase 1 — Python to JSON

A test case such as:

```python
browser = open_browser()

navigate(browser, "https://example.com")

username = find_element(browser, "username")

fill(username, "testuser")

close_browser(browser)
```

is analyzed by the AST parser.

The parser converts it into a generic representation similar to:

```json
{
    "name": "example",
    "steps": [
        {
            "action": "open_browser",
            "variable": "browser"
        },
        {
            "action": "navigate",
            "browser": "browser",
            "url": "https://example.com"
        },
        {
            "action": "find_element",
            "browser": "browser",
            "locator": "username",
            "variable": "username"
        },
        {
            "action": "fill",
            "element": "username",
            "value": "testuser"
        },
        {
            "action": "close_browser",
            "browser": "browser"
        }
    ]
}
```

The generated JSON is stored in:

```text
output/
```

The parser validates actions, argument counts, argument types, variable references, and supported Python statements.

---

## Phase 2 — JSON to Playwright

The generated test representation is passed to `PlaywrightExecutor`.

For each step, the executor dispatches the corresponding operation:

```text
action
  │
  ├── open_browser
  ├── navigate
  ├── find_element
  ├── click
  ├── fill
  ├── wait
  ├── screenshot
  └── close_browser
```

The executor measures each step's execution time and records whether the step passed or failed.

---

# Supported Actions

| Action          | Purpose                        | Example                                        |
| --------------- | ------------------------------ | ---------------------------------------------- |
| `open_browser`  | Opens a Chromium browser       | `browser = open_browser()`                     |
| `navigate`      | Navigates to a URL             | `navigate(browser, "https://example.com")`     |
| `find_element`  | Resolves a logical locator     | `username = find_element(browser, "username")` |
| `click`         | Clicks an element              | `click(username)`                              |
| `fill`          | Fills an input field           | `fill(username, "tomsmith")`                   |
| `wait`          | Waits for a specified duration | `wait(2000)`                                   |
| `screenshot`    | Captures the current page      | `screenshot(browser, "login_page")`            |
| `close_browser` | Closes the browser             | `close_browser(browser)`                       |

These actions are defined as framework vocabulary in `actions.py`. Their implementation is handled by the executor.

---

# Writing Test Cases

Test cases are stored in:

```text
test_cases/
```

## Example: Login Test

```python
from playwright_executor.actions import (
    open_browser,
    navigate,
    find_element,
    click,
    fill,
    wait,
    close_browser,
)

browser = open_browser()

navigate(
    browser,
    "https://the-internet.herokuapp.com/login"
)

username = find_element(browser, "username")
fill(username, "tomsmith")

password = find_element(browser, "password")
fill(password, "SuperSecretPassword!")

click(find_element(browser, "login"))

wait(2000)

close_browser(browser)
```

This example is included in the repository as `test_cases/login.py`.

---

# Installation

## Requirements

The project requires:

* Python `3.10+`
* Playwright
* Pytest

The project configuration specifies Python `>=3.10` and Playwright `>=1.40,<2.0`.

---

## 1. Clone the repository

```bash
git clone https://github.com/mahrane2002/playwright-test-executor.git
cd playwright-test-executor
```

---

## 2. Create a virtual environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install dependencies

Using `requirements.txt`:

```bash
pip install -r requirements.txt
```

The project currently declares Playwright and Pytest as dependencies.

Alternatively, install the project as a Python package:

```bash
pip install -e .
```

---

## 4. Install Playwright browsers

After installing Playwright, install the required browser:

```bash
playwright install chromium
```

The current executor launches Chromium in non-headless mode.

---

# Running a Test Case

The executor accepts a Python test case path from the command line.

Example:

```bash
python -m playwright_executor.executor test_cases/login.py
```

Another example:

```bash
python -m playwright_executor.executor test_cases/form.py
```

The execution process is:

```text
test_cases/login.py
        │
        ▼
     Parser
        │
        ▼
output/login.json
        │
        ▼
    Executor
        │
        ├── Browser execution
        ├── logs/login.log
        ├── screenshots/*
        └── reports/login_report.html
```

---

# Generated Artifacts

The framework uses dedicated directories for runtime artifacts.

```text
output/
├── login.json
├── form.json
└── ...

reports/
├── login_report.html
├── form_report.html
└── ...

screenshots/
├── login_page.png
└── ...

logs/
├── login.log
├── form.log
└── ...
```

Runtime-generated files are intentionally ignored by Git while the directories are preserved using `.gitkeep`.

This keeps the repository clean while allowing generated artifacts to exist locally.

---

# Execution Reports

Each execution generates an HTML report.

For example:

```text
reports/login_report.html
```

The report provides a summary similar to:

```text
Test Case: login

Status: PASSED
Total steps: 8
Successful steps: 8
Failed steps: 0
Execution duration: X.XX seconds
```

It also provides a detailed step table:

| Step | Action        | Status | Duration | Error |
| ---: | ------------- | ------ | -------: | ----- |
|    1 | open_browser  | PASSED |      ... | -     |
|    2 | navigate      | PASSED |      ... | -     |
|    3 | find_element  | PASSED |      ... | -     |
|    4 | fill          | PASSED |      ... | -     |
|    5 | find_element  | PASSED |      ... | -     |
|    6 | fill          | PASSED |      ... | -     |
|    7 | click         | PASSED |      ... | -     |
|    8 | close_browser | PASSED |      ... | -     |

If an execution fails, the report identifies the failed action and displays the associated error.

The reporter also marks steps that were not executed after an earlier failure as `NOT RUN`.

---

# Logging

Logging is configured per test case.

Example:

```text
logs/login.log
```

The logger writes messages to both the terminal and the log file.

Example log information includes:

```text
Starting test case: login
Executing step 1: open_browser
Browser opened and stored as 'browser'
Executing step 2: navigate
Navigating to https://...
Step 2 completed successfully
...
```

The logging system removes previous handlers before configuring a new test-case execution, preventing duplicated log messages.

---

# Object Repository

The Object Repository is located in:

```text
src/object_repository.py
```

It provides a mapping between business-friendly logical names and Playwright selectors.

Current mappings include:

```python
OBJECT_REPOSITORY = {
    "username": "#username",
    "password": "#password",
    "login": "button[type='submit']",
    "email": "#email",
    "retrieve_password": "#form_submit",
}
```

This allows test cases to use:

```python
username = find_element(browser, "username")
```

instead of embedding the selector directly into the test case.

The executor resolves the logical name through the Object Repository before creating the Playwright locator.

---

# Testing

The project includes automated tests under:

```text
tests/
```

Current test coverage includes:

```text
tests/
├── test_executor.py
├── test_form.py
├── test_login.py
├── test_navigation.py
├── test_parser.py
├── test_reporter.py
└── test_screenshot.py
```

The repository contains both unit-style tests using mocks and functional tests that execute the example test cases.

---

## Run the Test Suite

Use:

```bash
pytest
```

The Pytest configuration points to the `tests` directory.

---

# Test Categories

## Parser tests

`test_parser.py` validates:

* Valid test steps
* Unsupported actions
* Invalid argument counts
* Invalid argument types
* Invalid statements
* Parser validation behavior

For example, unsupported actions are expected to raise a `ValueError`.

---

## Executor tests

`test_executor.py` uses mocked Playwright objects to verify:

* Browser creation
* Page creation
* Navigation
* Locator resolution
* Input filling
* Browser cleanup
* Failure handling

The tests also verify that execution status changes to `FAILED` and that the failed action and error message are recorded when an operation raises an exception.

---

## Reporter tests

`test_reporter.py` verifies:

* Report generation
* PASSED status
* FAILED status
* Execution duration
* Step information
* Error reporting
* HTML escaping

HTML escaping is specifically tested to prevent raw HTML content from being inserted into generated reports.

---

## Functional tests

Functional tests execute real test cases such as:

```text
test_cases/form.py
test_cases/login.py
test_cases/navigation.py
test_cases/screenshot.py
```

and verify that the resulting execution status is `PASSED`.

These tests require a working browser environment and network access to the target websites.

---

# Error Handling

The executor follows a fail-fast execution model.

If a step raises an exception:

1. The step is marked as `FAILED`.
2. The execution duration is recorded.
3. The error message is stored.
4. The failed action is stored.
5. The error is logged.
6. Execution stops.
7. Remaining steps are reported as `NOT RUN`.
8. Resources are cleaned up.
9. An HTML report is generated.

This provides clear diagnostic information when a test fails.

---

# Design Principles

The project follows several important architectural principles.

## Separation of concerns

Each component has a specific responsibility:

| Component              | Responsibility                  |
| ---------------------- | ------------------------------- |
| `actions.py`           | Defines the test DSL            |
| `parser.py`            | Parses Python test cases        |
| `executor.py`          | Executes parsed actions         |
| `object_repository.py` | Stores logical locator mappings |
| `logger.py`            | Handles logging                 |
| `reporter.py`          | Generates HTML reports          |

This makes the framework easier to maintain and extend.

---

## Intermediate representation

The JSON representation acts as an intermediate layer between the test definition and browser automation.

```text
Python DSL
    ↓
AST
    ↓
JSON
    ↓
Playwright
```

This is an important architectural choice because it decouples the test syntax from the execution engine.

---

## No execution during parsing

The parser analyzes the source code using the AST instead of executing the test case.

This prevents browser operations from being triggered during the parsing phase.

---

# Current Limitations

The framework is intentionally lightweight and currently focuses on a limited set of browser operations.

Current limitations include:

### Browser support

The executor currently launches Chromium:

```python
self.playwright.chromium.launch(headless=False)
```

Firefox and WebKit are not currently exposed through the test DSL.

---

### Limited action set

Only the currently supported actions can be parsed and executed:

```text
open_browser
navigate
find_element
click
fill
wait
screenshot
close_browser
```

Adding additional operations requires changes to both the parser and executor.

---

### Limited Python syntax

The parser intentionally supports a restricted subset of Python.

For example, general control-flow constructs such as:

```python
for
while
if
```

are not supported as test-case statements.

This is deliberate: test files are treated as a controlled DSL rather than arbitrary Python programs.

---

### Fixed Object Repository

The current Object Repository is a Python dictionary.

A larger enterprise implementation could move locator definitions to:

* JSON
* YAML
* database
* configuration service
* Page Object Model

---

### Fixed browser configuration

The browser is currently launched in non-headless mode.

A future version could support configuration such as:

```text
headless = true
browser = chromium
viewport = ...
timeout = ...
```

---

# Extending the Framework

The framework is designed so that new capabilities can be added incrementally.

## Adding a new action

Suppose a future version needs:

```python
press(element, "Enter")
```

The implementation would require:

### 1. Add the action to `actions.py`

```python
def press(element, key):
    pass
```

### 2. Add it to `SUPPORTED_ACTIONS`

In `parser.py`:

```python
SUPPORTED_ACTIONS.add("press")
```

### 3. Implement parsing

The parser should validate the arguments and create the corresponding JSON representation.

Example:

```json
{
    "action": "press",
    "element": "username",
    "key": "Enter"
}
```

### 4. Add executor support

In `executor.py`:

```python
elif action == "press":
    self.press(step)
```

### 5. Implement the Playwright operation

```python
def press(self, step):
    element = self._get_variable(step["element"])
    element.press(step["key"])
```

### 6. Add automated tests

A new action should be covered by:

* parser tests
* executor tests
* functional tests where appropriate

---

# Recommended Enterprise Evolution

For production use in an enterprise environment, the following improvements could be considered.

## Configuration system

Introduce a central configuration file:

```text
config/
└── config.yaml
```

Possible settings:

```yaml
browser: chromium
headless: true
timeout: 30000
screenshot_on_failure: true
```

---

## Multiple browsers

Support:

```text
Chromium
Firefox
WebKit
```

and allow browser selection through configuration or command-line arguments.

---

## Better synchronization

Replace fixed waits such as:

```python
wait(2000)
```

with condition-based waits whenever possible.

For example:

```text
wait for element
wait for URL
wait for network state
wait for visibility
```

This would make tests more robust and reduce unnecessary execution time.

---

## Screenshot on failure

Automatically capture a screenshot whenever a step fails.

A useful failure package would contain:

```text
reports/
screenshots/
logs/
```

for easier debugging.

---

## Parallel execution

A future implementation could execute independent test cases in parallel to reduce total execution time.

---

## CI/CD integration

The executor can eventually be integrated into CI/CD platforms such as:

```text
GitHub Actions
GitLab CI
Jenkins
Azure DevOps
```

The pipeline could:

1. Install dependencies.
2. Install Playwright browsers.
3. Run test cases.
4. Collect reports.
5. Upload screenshots and logs.
6. Fail the pipeline if tests fail.

---

# Project Structure

The repository is organized around source code, test cases, automated tests, and generated artifacts.

```text
playwright-test-executor/
│
├── src/
│   ├── __init__.py
│   ├── actions.py
│   ├── executor.py
│   ├── logger.py
│   ├── object_repository.py
│   ├── parser.py
│   └── reporter.py
│
├── test_cases/
│   ├── form.py
│   ├── login.py
│   ├── navigation.py
│   └── screenshot.py
│
├── tests/
│   ├── test_executor.py
│   ├── test_form.py
│   ├── test_login.py
│   ├── test_navigation.py
│   ├── test_parser.py
│   ├── test_reporter.py
│   └── test_screenshot.py
│
├── output/
│   └── .gitkeep
│
├── reports/
│   └── .gitkeep
│
├── screenshots/
│   └── .gitkeep
│
├── logs/
│   └── .gitkeep
│
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

The runtime directories are intentionally kept in Git using `.gitkeep`, while generated contents are ignored.

---

# Troubleshooting

## `ModuleNotFoundError: No module named 'playwright_executor'`

The project currently uses imports such as:

```python
from playwright_executor.executor import PlaywrightExecutor
```

and the package configuration expects packages to be discovered under `src`.

Before using the project in a new environment, verify that the package is structured consistently with the configured package name.

The recommended final structure is:

```text
src/
└── playwright_executor/
    ├── __init__.py
    ├── actions.py
    ├── executor.py
    ├── logger.py
    ├── object_repository.py
    ├── parser.py
    └── reporter.py
```

This should be resolved before the project is handed over as a reusable enterprise package.

---

## Browser is not installed

Run:

```bash
playwright install chromium
```

---

## Tests fail because a website is unavailable

Functional tests access external websites.

If the target website is unavailable, the functional tests may fail even if the framework itself is working correctly.

For framework-level testing, the mocked executor tests do not require a real browser session.

---

# Development Workflow

A typical development workflow is:

```text
1. Define/modify a test action
          ↓
2. Update actions.py
          ↓
3. Update parser.py
          ↓
4. Update executor.py
          ↓
5. Update tests
          ↓
6. Run pytest
          ↓
7. Execute functional examples
          ↓
8. Review logs/reports
          ↓
9. Commit changes
```

This workflow helps ensure that new features are implemented consistently across all framework layers.

---

# Future Improvements

Potential future versions could introduce:

* [ ] Firefox and WebKit support
* [ ] Headless/headed configuration
* [ ] Configurable browser settings
* [ ] Configurable timeouts
* [ ] Automatic screenshots on failure
* [ ] Explicit Playwright waits
* [ ] Assertions
* [ ] Text and URL validation
* [ ] More browser actions
* [ ] Page Object Model support
* [ ] External Object Repository
* [ ] Test tagging
* [ ] Test suites
* [ ] Parallel execution
* [ ] Retry mechanism
* [ ] CI/CD integration
* [ ] Centralized configuration
* [ ] Enhanced reporting
* [ ] Test execution history
* [ ] Cross-browser execution
* [ ] Enterprise-level test management integration

---

# Conclusion

Playwright Test Executor provides a lightweight architecture for browser test automation based on a controlled Python test DSL.

Its main architectural flow is:

```text
Python Test Definition
        ↓
      AST
        ↓
Generic JSON Representation
        ↓
Playwright Execution
        ↓
 ┌──────┼────────┐
 ↓      ↓        ↓
Logs  Reports  Screenshots
```

The separation between parsing and execution provides a strong foundation for future extensions while keeping the current implementation simple and understandable.

The project can serve as a foundation for a more complete enterprise-grade test automation framework by progressively adding configuration management, synchronization mechanisms, assertions, cross-browser execution, parallelism, CI/CD integration, and richer reporting.

---

# License

This project is currently provided as a project/research implementation.

Add an explicit license file such as `LICENSE` before distributing the project externally or incorporating it into an organization's production environment.
