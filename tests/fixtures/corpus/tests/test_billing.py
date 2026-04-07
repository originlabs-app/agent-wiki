"""Tests for the billing module."""
from src.billing import calculate_cost, PlanTier, PLAN_LIMITS


def test_calculate_cost_free():
    assert calculate_cost(0) == 0
    assert calculate_cost(500) == 5  # 500 * 10 / 1000 = 5


def test_calculate_cost_threshold():
    assert calculate_cost(100) == 1
    assert calculate_cost(99) == 0


def test_plan_limits():
    assert PLAN_LIMITS[PlanTier.FREE]["scans_per_month"] == 100
    assert PLAN_LIMITS[PlanTier.ENTERPRISE]["scans_per_month"] == -1
