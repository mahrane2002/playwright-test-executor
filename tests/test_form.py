from actions import (
    open_browser,
    navigate,
    find_element,
    fill,
    click,
    wait,
    close_browser,
)

browser = open_browser()

navigate(browser, "https://the-internet.herokuapp.com/forgot_password")

email = find_element(browser, "email")
fill(email, "test@example.com")

click(find_element(browser, "retrieve_password"))

wait(2000)

close_browser(browser)
