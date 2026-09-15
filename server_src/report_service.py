# AI生成
"""Report generation service — produces Markdown and HTML assessment reports."""
import markdown
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class ReportService:
    """Generates assessment reports in Markdown and HTML format."""

    def __init__(self, report_dir: Path):
        self.report_dir = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        task_name: str,
        benchmark: str,
        server_results: List[Dict],
        summary: Dict,
        executive_summary: str = "",
    ) -> Dict:
        """Generate both Markdown and HTML reports for a task.

        Args:
            task_name: name of the assessment task
            benchmark: benchmark used (CIS/STIG)
            server_results: per-server assessment results
            summary: task summary statistics
            executive_summary: LLM-generated executive summary

        Returns:
            dict with markdown_path, html_path, markdown_content, html_content
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_name = "".join(c for c in task_name if c.isalnum() or c in (' ', '-', '_')).strip()
        file_base = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Generate Markdown
        md_content = self._generate_markdown(
            task_name, benchmark, server_results, summary, executive_summary, timestamp
        )

        # Generate HTML from Markdown
        html_content = self._generate_html(
            task_name, benchmark, server_results, summary, executive_summary, timestamp
        )

        # Write files
        md_path = self.report_dir / f"{file_base}.md"
        html_path = self.report_dir / f"{file_base}.html"

        md_path.write_text(md_content, encoding="utf-8")
        html_path.write_text(html_content, encoding="utf-8")

        return {
            "markdown_path": str(md_path),
            "html_path": str(html_path),
            "markdown_content": md_content,
            "html_content": html_content,
        }

    def _generate_markdown(
        self,
        task_name: str,
        benchmark: str,
        server_results: List[Dict],
        summary: Dict,
        executive_summary: str,
        timestamp: str,
    ) -> str:
        """Generate Markdown report content."""
        lines = [
            f"# VM Security Hardening Assessment Report",
            f"",
            f"**Task Name:** {task_name}",
            f"**Benchmark:** {benchmark}",
            f"**Assessment Date:** {timestamp}",
            f"**Report Type:** Per-task Summary (All Servers)",
            f"",
            f"---",
            f"",
            f"## Executive Summary",
            f"",
            f"{executive_summary if executive_summary else 'No executive summary available.'}",
            f"",
            f"## Assessment Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Servers | {summary.get('total_servers', 0)} |",
            f"| Successful Assessments | {summary.get('successful', 0)} |",
            f"| Failed Assessments | {summary.get('failed', 0)} |",
            f"| Total Controls Checked | {summary.get('total_controls', 0)} |",
            f"| Compliant | {summary.get('compliant', 0)} |",
            f"| Non-Compliant | {summary.get('non_compliant', 0)} |",
            f"| Unknown / Insufficient Data | {summary.get('unknown', 0)} |",
            f"| Compliance Rate | {summary.get('compliance_rate', 'N/A')} |",
            f"",
            f"---",
            f"",
        ]

        # Per-server results
        for server in server_results:
            ip = server.get("server_ip", "Unknown")
            status = server.get("status", "Unknown")
            error = server.get("error")
            server_benchmark = server.get("benchmark", benchmark)

            lines.extend([
                f"## Server: {ip} ({server_benchmark})",
                f"",
                f"- **Status:** {status}",
                f"",
            ])

            if error:
                lines.extend([
                    f"**Error:** {error}",
                    f"",
                ])
                continue

            controls = server.get("controls_assessed", [])
            if not controls:
                lines.extend([
                    f"No controls were assessed for this server.",
                    f"",
                ])
                continue

            # Controls table
            lines.extend([
                f"### Control Assessment Results",
                f"",
                f"| Control ID | Title | Compliant | Risk Level | Current Value | Expected Value |",
                f"|-----------|-------|-----------|------------|--------------|---------------|",
            ])

            for ctrl in controls:
                compliant = ctrl.get("compliant")
                if compliant is True:
                    status_icon = "✅ Yes"
                elif compliant is False:
                    status_icon = "❌ No"
                else:
                    status_icon = "⚠️ Unknown"

                ctrl_id = ctrl.get("control_id", "N/A")
                title = ctrl.get("control_title", "N/A")
                risk = ctrl.get("risk_level", "N/A")
                current = str(ctrl.get("current_value", "N/A")).replace("|", "\\|")[:50]
                expected = str(ctrl.get("expected_value", "N/A")).replace("|", "\\|")[:50]

                lines.append(f"| {ctrl_id} | {title} | {status_icon} | {risk} | {current} | {expected} |")

            lines.append("")

            # Detailed analysis for non-compliant controls
            non_compliant = [c for c in controls if c.get("compliant") is False]
            if non_compliant:
                lines.extend([
                    f"### Detailed Analysis & Optimization Suggestions",
                    f"",
                ])
                for ctrl in non_compliant:
                    lines.extend([
                        f"#### {ctrl.get('control_id', '')}: {ctrl.get('control_title', '')}",
                        f"",
                        f"- **Risk Level:** {ctrl.get('risk_level', 'N/A')}",
                        f"- **Current Value:** {ctrl.get('current_value', 'N/A')}",
                        f"- **Expected Value:** {ctrl.get('expected_value', 'N/A')}",
                        f"- **Analysis:** {ctrl.get('analysis', 'N/A')}",
                        f"- **Optimization Suggestion:** {ctrl.get('suggestion', 'N/A')}",
                        f"",
                    ])

            lines.extend([
                f"---",
                f"",
            ])

        lines.extend([
            f"## Report Footer",
            f"",
            f"*Generated by ECS VM Security Hardening Assessment Console*",
            f"*This is a read-only assessment report. No server configurations were modified.*",
        ])

        return "\n".join(lines)

    def _generate_html(
        self,
        task_name: str,
        benchmark: str,
        server_results: List[Dict],
        summary: Dict,
        executive_summary: str,
        timestamp: str,
    ) -> str:
        """Generate styled HTML report content."""
        # Build HTML directly for better styling control
        server_sections = []

        for server in server_results:
            ip = server.get("server_ip", "Unknown")
            status = server.get("status", "Unknown")
            error = server.get("error")
            server_benchmark = server.get("benchmark", benchmark)

            status_class = "status-success" if status == "completed" else "status-failed"

            section = f"""
    <div class="server-section">
        <h2 class="server-title">🖥️ Server: {ip} <span class="badge" style="background:#1e88e5;color:white;font-size:0.7em;">{server_benchmark}</span></h2>
        <div class="server-meta">
            <span class="badge {status_class}">{status}</span>
        </div>"""

            if error:
                section += f"""
        <div class="error-box">❌ Error: {error}</div>"""
            else:
                controls = server.get("controls_assessed", [])
                if controls:
                    section += """
        <table class="controls-table">
            <thead>
                <tr>
                    <th>Control ID</th>
                    <th>Title</th>
                    <th>Compliant</th>
                    <th>Risk Level</th>
                    <th>Current Value</th>
                    <th>Expected Value</th>
                </tr>
            </thead>
            <tbody>"""

                    for ctrl in controls:
                        compliant = ctrl.get("compliant")
                        if compliant is True:
                            icon = "✅"
                            cls = "compliant-yes"
                        elif compliant is False:
                            icon = "❌"
                            cls = "compliant-no"
                        else:
                            icon = "⚠️"
                            cls = "compliant-unknown"

                        risk = ctrl.get("risk_level", "N/A")
                        risk_cls = f"risk-{risk.lower()}" if risk else ""

                        section += f"""
                <tr class="{cls}">
                    <td>{ctrl.get('control_id', 'N/A')}</td>
                    <td>{ctrl.get('control_title', 'N/A')}</td>
                    <td>{icon}</td>
                    <td class="{risk_cls}">{risk}</td>
                    <td>{ctrl.get('current_value', 'N/A')}</td>
                    <td>{ctrl.get('expected_value', 'N/A')}</td>
                </tr>"""

                    section += """
            </tbody>
        </table>"""

                    # Non-compliant details
                    non_compliant = [c for c in controls if c.get("compliant") is False]
                    if non_compliant:
                        section += """
        <div class="details-section">
            <h3>📋 Detailed Analysis & Optimization Suggestions</h3>"""
                        for ctrl in non_compliant:
                            section += f"""
            <div class="control-detail">
                <h4>{ctrl.get('control_id', '')}: {ctrl.get('control_title', '')}</h4>
                <p><strong>Risk Level:</strong> <span class="risk-{str(ctrl.get('risk_level', '')).lower()}">{ctrl.get('risk_level', 'N/A')}</span></p>
                <p><strong>Current Value:</strong> {ctrl.get('current_value', 'N/A')}</p>
                <p><strong>Expected Value:</strong> {ctrl.get('expected_value', 'N/A')}</p>
                <p><strong>Analysis:</strong> {ctrl.get('analysis', 'N/A')}</p>
                <div class="suggestion-box">
                    <strong>💡 Optimization Suggestion:</strong> {ctrl.get('suggestion', 'N/A')}
                </div>
            </div>"""
                        section += """
        </div>"""

            section += """
    </div>"""
            server_sections.append(section)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Assessment Report - {task_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a237e; border-bottom: 3px solid #1a237e; padding-bottom: 10px; margin-bottom: 20px; }}
        h2 {{ color: #283593; margin: 20px 0 10px; }}
        h3 {{ color: #303f9f; margin: 15px 0 8px; }}
        h4 {{ color: #1e88e5; margin: 10px 0 5px; }}
        .meta {{ background: #e8eaf6; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .meta p {{ margin: 5px 0; }}
        .summary-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; background: white; }}
        .summary-table th, .summary-table td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        .summary-table th {{ background: #1a237e; color: white; }}
        .server-section {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .server-title {{ border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.9em; margin-right: 8px; }}
        .badge-db {{ background: #e3f2fd; color: #1565c0; }}
        .status-success {{ background: #c8e6c9; color: #2e7d32; }}
        .status-failed {{ background: #ffcdd2; color: #c62828; }}
        .controls-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 0.9em; }}
        .controls-table th {{ background: #37474f; color: white; padding: 8px; text-align: left; }}
        .controls-table td {{ border: 1px solid #e0e0e0; padding: 8px; }}
        .compliant-yes {{ background: #f1f8e9; }}
        .compliant-no {{ background: #fff3e0; }}
        .compliant-unknown {{ background: #fce4ec; }}
        .risk-high {{ color: #c62828; font-weight: bold; }}
        .risk-medium {{ color: #ef6c00; }}
        .risk-low {{ color: #2e7d32; }}
        .error-box {{ background: #ffebee; border-left: 4px solid #c62828; padding: 10px; margin: 10px 0; border-radius: 3px; }}
        .details-section {{ margin-top: 20px; padding-top: 15px; border-top: 1px solid #e0e0e0; }}
        .control-detail {{ background: #fafafa; border-left: 3px solid #1e88e5; padding: 12px; margin: 10px 0; border-radius: 3px; }}
        .suggestion-box {{ background: #fffde7; border: 1px solid #fdd835; padding: 10px; margin-top: 8px; border-radius: 3px; }}
        .footer {{ text-align: center; color: #9e9e9e; margin-top: 30px; font-size: 0.85em; }}
        .exec-summary {{ background: #e8f5e9; border-left: 4px solid #43a047; padding: 15px; margin: 15px 0; border-radius: 3px; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 VM Security Hardening Assessment Report</h1>

        <div class="meta">
            <p><strong>Task Name:</strong> {task_name}</p>
            <p><strong>Benchmark:</strong> {benchmark}</p>
            <p><strong>Assessment Date:</strong> {timestamp}</p>
            <p><strong>Report Type:</strong> Per-task Summary (All Servers)</p>
        </div>

        <h2>📊 Executive Summary</h2>
        <div class="exec-summary">{executive_summary if executive_summary else 'No executive summary available.'}</div>

        <h2>📈 Assessment Summary</h2>
        <table class="summary-table">
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Servers</td><td>{summary.get('total_servers', 0)}</td></tr>
            <tr><td>Successful Assessments</td><td>{summary.get('successful', 0)}</td></tr>
            <tr><td>Failed Assessments</td><td>{summary.get('failed', 0)}</td></tr>
            <tr><td>Total Controls Checked</td><td>{summary.get('total_controls', 0)}</td></tr>
            <tr><td>Compliant</td><td>{summary.get('compliant', 0)}</td></tr>
            <tr><td>Non-Compliant</td><td>{summary.get('non_compliant', 0)}</td></tr>
            <tr><td>Unknown / Insufficient Data</td><td>{summary.get('unknown', 0)}</td></tr>
            <tr><td>Compliance Rate</td><td><strong>{summary.get('compliance_rate', 'N/A')}</strong></td></tr>
        </table>

        <h2>🖥️ Per-Server Results</h2>
        {''.join(server_sections)}

        <div class="footer">
            <p>Generated by ECS VM Security Hardening Assessment Console</p>
            <p>This is a read-only assessment report. No server configurations were modified.</p>
        </div>
    </div>
</body>
</html>"""

        return html
