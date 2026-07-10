"""Scan diff engine for regressions and improvements."""

from __future__ import annotations

from typing import Any

from agentworthy.models import Check, CheckStatus, Simulation, SimulationOutcome


def diff_scans(
    prev_checks: list[Check],
    curr_checks: list[Check],
    prev_sims: list[Simulation],
    curr_sims: list[Simulation],
    prev_score: int | None,
    curr_score: int | None,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    prev_map = {c.check_key: c for c in prev_checks}
    for c in curr_checks:
        p = prev_map.get(c.check_key)
        if p and p.status == CheckStatus.PASS and c.status == CheckStatus.FAIL:
            alerts.append({
                "type": "check_regression",
                "check_key": c.check_key,
                "before": p.status.value,
                "after": c.status.value,
            })
        if p and p.status == CheckStatus.FAIL and c.status == CheckStatus.PASS:
            alerts.append({"type": "check_regression", "check_key": c.check_key, "improvement": True})

    if prev_score is not None and curr_score is not None and prev_score - curr_score >= 5:
        alerts.append({
            "type": "score_drop",
            "before": prev_score,
            "after": curr_score,
            "delta": curr_score - prev_score,
        })

    prev_sims_map = {s.task_key: s for s in prev_sims}
    for s in curr_sims:
        p = prev_sims_map.get(s.task_key)
        if p and p.outcome == SimulationOutcome.SUCCESS and s.outcome == SimulationOutcome.FAIL:
            alerts.append({"type": "simulation_regression", "task_key": s.task_key})

    return alerts
