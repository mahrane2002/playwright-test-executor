from actions import (
    open_browser,
    navigate,
    wait,
    close_browser,
)

browser = open_browser()

navigate(browser, "https://the-internet.herokuapp.com")

wait(1500)

close_browser(browser)
