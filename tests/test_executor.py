import pytest
from unittest.mock import MagicMock, patch
from playwright_executor.executor import PlaywrightExecutor

def test_executor_variables_and_flow():
    # Construct a valid JSON test case representation
    test_case = {
        "name": "test_mock_case",
        "steps": [
            {"action": "open_browser", "variable": "browser"},
            {"action": "navigate", "browser": "browser", "url": "https://example.com"},
            {"action": "find_element", "browser": "browser", "locator": "username", "variable": "username_elem"},
            {"action": "fill", "element": "username_elem", "value": "testuser"},
            {"action": "close_browser", "browser": "browser"}
        ]
    }
    
    executor = PlaywrightExecutor(test_case)
    
    # Mock playwright objects
    mock_playwright = MagicMock()
    mock_browser = MagicMock()
    mock_page = MagicMock()
    mock_element = MagicMock()
    
    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_page.return_value = mock_page
    mock_page.locator.return_value = mock_element
    
    # We patch sync_playwright
    with patch("playwright_executor.executor.sync_playwright") as mock_sync_pw:
        mock_sync_pw.return_value.start.return_value = mock_playwright
        
        # Run execution
        executor.execute()
        
        # Assertions
        assert executor.status == "PASSED"
        mock_playwright.chromium.launch.assert_called_once_with(headless=False)
        mock_browser.new_page.assert_called_once()
        mock_page.goto.assert_called_once_with("https://example.com", wait_until="domcontentloaded")
        mock_page.locator.assert_called_once_with("#username") # Resolves logical locator to selector
        mock_element.fill.assert_called_once_with("testuser")
        mock_browser.close.assert_called_once()

def test_executor_error_handling():
    test_case = {
        "name": "test_mock_fail",
        "steps": [
            {"action": "open_browser", "variable": "browser"},
            {"action": "navigate", "browser": "browser", "url": "https://example.com"},
            {"action": "find_element", "browser": "browser", "locator": "username", "variable": "username_elem"},
        ]
    }
    executor = PlaywrightExecutor(test_case)
    
    mock_playwright = MagicMock()
    mock_browser = MagicMock()
    mock_page = MagicMock()
    
    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.side_effect = Exception("Connection Refused")
    
    with patch("playwright_executor.executor.sync_playwright") as mock_sync_pw:
        mock_sync_pw.return_value.start.return_value = mock_playwright
        
        with pytest.raises(Exception, match="Connection Refused"):
            executor.execute()
            
        assert executor.status == "FAILED"
        assert executor.failed_action == "navigate"
        assert "Connection Refused" in executor.error_message
