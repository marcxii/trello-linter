"""CSV exporter for report data.

Uses the report context shape from report_builder to emit a sectioned CSV.
The "Findings by Rule" section is driven by a normalized rule table so new
rules can be added without changing export code.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Iterable


def _join_list(values: Iterable[str] | None) -> str:
    if not values:
        return ""
    return "; ".join([str(v) for v in values if v is not None])


def build_report_csv(report_ctx: dict[str, Any]) -> str:
    """Render report context as a CSV string matching report sections."""
    output = StringIO()
    writer = csv.writer(output)

    run = report_ctx.get("run", {})
    report = report_ctx.get("report", {})
    board = report_ctx.get("board", {})
    scores = report_ctx.get("scores", {})
    generated_at = report_ctx.get("generated_at", "")

    def row(cells: list[str]) -> None:
        writer.writerow(cells)

    def section(title: str) -> None:
        row([title])

    def spacer() -> None:
        row([])

    # Run metadata (minimal)
    section("Run Info")
    row(["run_id", str(run.get("id", ""))])
    row(["created_at", str(run.get("created_at", ""))])
    spacer()

    # Quick stats (report section)
    section("Quick Stats")
    row(["board", str(board.get("name", ""))])
    row(["created", str(generated_at)])
    row(["cards", str(board.get("cards_count", ""))])
    row(["lists", str(board.get("lists_count", ""))])
    row(["members", str(board.get("members_count", ""))])
    spacer()

    # Scorecard
    section("Scorecard")
    row(["overall_score", str(scores.get("overall_score", ""))])
    row(["total_findings", str(scores.get("total_findings", ""))])
    if "overdue_count" in scores:
        row(["overdue_count", str(scores.get("overdue_count", ""))])
    spacer()
    # Findings
    section("Findings")
    findings = report.get("findings", []) or []
    for idx, finding in enumerate(findings, start=1):
        if isinstance(finding, dict):
            row([f"{idx}.title", str(finding.get("title", finding.get("rule", "Finding")))])
            row([f"{idx}.severity", str(finding.get("severity", ""))])
            row([f"{idx}.message", str(finding.get("message", finding.get("description", "")))])
            row([f"{idx}.cards", str(finding.get("card_ids", finding.get("cards", "")))])
        else:
            row([f"{idx}.message", str(finding)])
    spacer()

    # Findings by Rule (normalized table)
    section("Findings by Rule")
    rule_columns = report_ctx.get("rule_columns") or ["Rule", "Card", "List", "Members", "Due_date"]
    rule_rows = report_ctx.get("rule_rows") or []
    row([str(col) for col in rule_columns])
    for rule_row in rule_rows:
        if isinstance(rule_row, (list, tuple)):
            row([str(cell) for cell in rule_row])
        elif isinstance(rule_row, dict):
            row([str(rule_row.get(col, "")) for col in rule_columns])
    spacer()

    return output.getvalue()

    
    
