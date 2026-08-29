from playwright_executor.actions import (
    open_browser,
    navigate,
    wait,
    close_browser,
)

browser = open_browser()

navigate(browser, "https://example.com")

wait(1000)

navigate(browser, "https://the-internet.herokuapp.com")

wait(1000)

close_browser(browser)
