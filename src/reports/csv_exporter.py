

"""CSV exporter for report data."""

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

    # Findings by Rule (Past-due active work)
    section("Findings by Rule")
    row(["Rule", "Card", "List", "Members", "Due_date"])
    overdue_cards = report_ctx.get("overdue_cards") or []
    for idx, card in enumerate(overdue_cards, start=1):
        members = card.get("members") or []
        if not members:
            members = [""]
        for member_index, member in enumerate(members):
            if member_index == 0:
                row([
                    "Past-due active work",
                    str(card.get("name", "")),
                    str(card.get("list_name", "")),
                    str(member),
                    str(card.get("due", ""))[:10],
                ])
            else:
                row(["", "", "", str(member), ""])
    spacer()

    return output.getvalue()

    
    
