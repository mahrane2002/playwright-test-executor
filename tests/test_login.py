from actions import (
    open_browser,
    navigate,
    find_element,
    click,
    fill,
    wait,
    close_browser,
)

browser = open_browser()

navigate(browser, "https://the-internet.herokuapp.com/login")

username = find_element(browser, "username")
fill(username, "tomsmith")

password = find_element(browser, "password")
fill(password, "SuperSecretPassword!")

click(find_element(browser, "login"))

wait(2000)

close_browser(browser)
