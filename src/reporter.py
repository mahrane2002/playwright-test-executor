from html import escape
from pathlib import Path

REPORT_DIR = Path("reports")

class HTMLReporter:
    """
    Responsible for generating HTML execution reports.
    """
    def __init__(self, test_case, status, steps_stats, start_time, end_time, error_message=None, failed_action=None):
        self.test_case = test_case
        self.status = status
        self.steps_stats = steps_stats
        self.start_time = start_time
        self.end_time = end_time
        self.error_message = error_message
        self.failed_action = failed_action

    def generate(self):
        REPORT_DIR.mkdir(exist_ok=True)
        test_name = self.test_case["name"]

        duration = (
            self.end_time - self.start_time
            if self.start_time and self.end_time
            else 0.0
        )

        total_steps = len(self.test_case["steps"])

        successful_steps = sum(
            1
            for s in self.steps_stats
            if s["status"] == "PASSED"
        )

        failed_steps = sum(
            1
            for s in self.steps_stats
            if s["status"] == "FAILED"
        )

        # Escape dynamic values
        safe_test_name = escape(str(test_name))
        safe_status = escape(str(self.status))

        safe_error = (
            escape(str(self.error_message))
            if self.error_message
            else ""
        )

        safe_action = (
            escape(str(self.failed_action))
            if self.failed_action
            else ""
        )

        # Build steps rows for the HTML table
        table_rows = ""

        for s in self.steps_stats:
            action = escape(str(s["action"]))
            status = escape(str(s["status"]))
            error = (
                escape(str(s["error"]))
                if s["error"]
                else None
            )

            err_cell = (
                f"<td style='color: red;'>{error}</td>"
                if error
                else "<td>-</td>"
            )

            status_color = (
                "green"
                if s["status"] == "PASSED"
                else "red"
            )

            table_rows += f"""
            <tr>
                <td>{s["step"]}</td>
                <td>{action}</td>
                <td style='color: {status_color}; font-weight: bold;'>
                    {status}
                </td>
                <td>{s["duration"]:.3f}s</td>
                {err_cell}
            </tr>
            """

        # Add unexecuted steps
        executed_count = len(self.steps_stats)

        if executed_count < total_steps:
            for index in range(executed_count + 1, total_steps + 1):
                step = self.test_case["steps"][index - 1]
                action = escape(str(step["action"]))

                table_rows += f"""
                <tr style='color: #888;'>
                    <td>{index}</td>
                    <td>{action}</td>
                    <td>NOT RUN</td>
                    <td>-</td>
                    <td>-</td>
                </tr>
                """

        report_file = REPORT_DIR / f"{test_name}_report.html"

        error_section = ""
        if self.status == "FAILED":
            error_section = f"""
            <div class="error-box">
                <strong>Failed Action:</strong>
                {safe_action}
                <br>

                <strong>Error Details:</strong>
                {safe_error}
            </div>
            """

        status_class = f"status-{self.status.lower()}"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Test Execution Report - {safe_test_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            background-color: #f8f9fa;
            color: #333;
        }}
        h1 {{
            color: #0056b3;
            border-bottom: 2px solid #0056b3;
            padding-bottom: 10px;
        }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 30px;
        }}
        .metric {{
            margin-bottom: 12px;
            font-size: 16px;
        }}
        .label {{
            font-weight: bold;
            width: 220px;
            display: inline-block;
        }}
        .status-passed {{
            color: #28a745;
            font-weight: bold;
            background: #d4edda;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .status-failed {{
            color: #dc3545;
            font-weight: bold;
            background: #f8d7da;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .error-box {{
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
            font-family: monospace;
            white-space: pre-wrap;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background-color: #0056b3;
            color: white;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        tr:nth-child(even) {{
            background-color: #f1f3f5;
        }}
    </style>
</head>
<body>
    <h1>Test Case: {safe_test_name}</h1>
    <div class="summary">
        <div class="metric">
            <span class="label">Status:</span>
            <span class="{status_class}">{safe_status}</span>
        </div>
        <div class="metric">
            <span class="label">Total steps:</span>
            {total_steps}
        </div>
        <div class="metric">
            <span class="label">Successful steps:</span>
            {successful_steps}
        </div>
        <div class="metric">
            <span class="label">Failed steps:</span>
            {failed_steps}
        </div>
        <div class="metric">
            <span class="label">Execution duration:</span>
            {duration:.2f} seconds
        </div>
        {error_section}
    </div>
    <h2>Steps Execution Details</h2>
    <table>
        <thead>
            <tr>
                <th>Step</th>
                <th>Action</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Error Details</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
</body>
</html>
"""
        report_file.write_text(html_content, encoding="utf-8")
        from playwright_executor.logger import logger
        logger.info("HTML report generated: %s", report_file)
