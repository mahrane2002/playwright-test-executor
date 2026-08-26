"""
Generic action definitions used by the Python test-case DSL.

These functions intentionally contain no Playwright implementation.
They only define the vocabulary that can be used inside test cases.
"""


def open_browser():
    pass


def navigate(browser, url):
    pass


def find_element(browser, locator):
    pass


def click(element):
    pass


def fill(element, value):
    pass


def wait(duration):
    pass


def screenshot(browser, name):
    pass


def close_browser(browser):
    pass