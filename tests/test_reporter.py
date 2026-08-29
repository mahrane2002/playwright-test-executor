import pytest
from pathlib import Path
from playwright_executor.reporter import HTMLReporter

def test_reporter_passed(tmp_path, monkeypatch):
    # Patch REPORT_DIR to a temporary directory for isolated testing
    report_dir = tmp_path / "reports"
    monkeypatch.setattr("playwright_executor.reporter.REPORT_DIR", report_dir)
    
    test_case = {
        "name": "test_passed_flow",
        "steps": [
            {"action": "open_browser"},
            {"action": "navigate"}
        ]
    }
    steps_stats = [
        {"step": 1, "action": "open_browser", "status": "PASSED", "duration": 0.5, "error": None},
        {"step": 2, "action": "navigate", "status": "PASSED", "duration": 1.2, "error": None}
    ]
    
    reporter = HTMLReporter(
        test_case=test_case,
        status="PASSED",
        steps_stats=steps_stats,
        start_time=100.0,
        end_time=102.5
    )
    reporter.generate()
    
    report_file = report_dir / "test_passed_flow_report.html"
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    
    assert "Test Execution Report - test_passed_flow" in content
    assert "status-passed" in content
    assert "PASSED" in content
    assert "2.50 seconds" in content
    assert "open_browser" in content
    assert "navigate" in content

def test_reporter_failed_and_escaping(tmp_path, monkeypatch):
    report_dir = tmp_path / "reports"
    monkeypatch.setattr("playwright_executor.reporter.REPORT_DIR", report_dir)
    
    test_case = {
        "name": "test_failed_flow",
        "steps": [
            {"action": "open_browser"},
            {"action": "navigate"}
        ]
    }
    steps_stats = [
        {"step": 1, "action": "open_browser", "status": "PASSED", "duration": 0.4, "error": None},
        {"step": 2, "action": "navigate", "status": "FAILED", "duration": 0.8, "error": "Failed to load <script>alert('xss')</script>"}
    ]
    
    reporter = HTMLReporter(
        test_case=test_case,
        status="FAILED",
        steps_stats=steps_stats,
        start_time=100.0,
        end_time=101.5,
        error_message="Failed to load <script>alert('xss')</script>",
        failed_action="navigate"
    )
    reporter.generate()
    
    report_file = report_dir / "test_failed_flow_report.html"
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    
    assert "status-failed" in content
    assert "FAILED" in content
    
    # HTML escaping checks
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in content
    assert "<script>alert('xss')</script>" not in content
    assert "Failed Action:" in content
    assert "navigate" in content
