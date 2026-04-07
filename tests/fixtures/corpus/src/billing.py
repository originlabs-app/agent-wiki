"""Billing module — usage tracking and invoice generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# from .auth import User
# from .db import get_connection
# from .utils import generate_id


class PlanTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLAN_LIMITS = {
    PlanTier.FREE: {"scans_per_month": 100, "max_nodes": 1000},
    PlanTier.PRO: {"scans_per_month": 10000, "max_nodes": 100000},
    PlanTier.ENTERPRISE: {"scans_per_month": -1, "max_nodes": -1},
}


@dataclass
class UsageRecord:
    user_id: str
    operation: str  # "scan" | "query" | "ingest"
    tokens_used: int
    timestamp: float


@dataclass
class Invoice:
    id: str
    user_id: str
    period: str
    total_tokens: int
    amount_cents: int
    line_items: list[dict] = field(default_factory=list)


def calculate_cost(tokens: int) -> int:
    """$0.01 per 1000 tokens, minimum $0."""
    return max(0, (tokens * 10) // 1000)


def _calculate_cost(tokens: int) -> int:
    """Legacy alias for calculate_cost."""
    return calculate_cost(tokens)
