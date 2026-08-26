from actions import (
    open_browser,
    navigate,
    screenshot,
    close_browser,
)

browser = open_browser()

navigate(browser, "https://the-internet.herokuapp.com/login")

screenshot(browser, "login_page")

close_browser(browser)
