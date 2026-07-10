"""Plan limits — single source of truth."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanLimits:
    name: str
    price_usd: int
    max_sites: int
    pages_per_scan: int
    simulations_per_scan: int
    scan_frequency: str  # manual | weekly | daily
    api_access: bool
    max_seats: int
    fixes_blurred: bool


PLAN_LIMITS: dict[str, PlanLimits] = {
    "free": PlanLimits("Free", 0, 1, 25, 0, "manual", False, 1, True),
    "starter": PlanLimits("Starter", 29, 3, 100, 1, "weekly", False, 1, False),
    "pro": PlanLimits("Pro", 79, 10, 200, 3, "daily", True, 3, False),
    "agency": PlanLimits("Agency", 199, 50, 200, 5, "daily", True, 10, False),
}


def get_plan_limits(plan: str) -> PlanLimits:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
