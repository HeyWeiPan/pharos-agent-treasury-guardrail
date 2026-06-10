from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def decimal_to_str(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True)
class GuardrailPolicy:
    agent_id: str
    chain_id: str
    token_symbol: str
    daily_limit: Decimal
    per_tx_limit: Decimal
    human_approval_threshold: Decimal
    allowed_destinations: List[str] = field(default_factory=list)
    blocked_destinations: List[str] = field(default_factory=list)
    require_destination_screening: bool = False
    screening_block_level: str = "CRITICAL"
    screening_warn_level: str = "HIGH"

    def to_json(self) -> Dict[str, Any]:
        payload = asdict(self)
        for key in ("daily_limit", "per_tx_limit", "human_approval_threshold"):
            payload[key] = decimal_to_str(payload[key])
        return payload


@dataclass(frozen=True)
class SpendRequest:
    agent_id: str
    chain_id: str
    token_symbol: str
    destination: str
    amount: Decimal
    purpose: str
    request_id: str

    def to_json(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["amount"] = decimal_to_str(self.amount)
        return payload


@dataclass(frozen=True)
class DestinationScreening:
    destination: str
    verdict: str
    risk_level: str
    confidence: float
    reasons: List[str] = field(default_factory=list)
    checked_at: str = field(default_factory=utc_now_iso)

    @property
    def blocks_spend(self) -> bool:
        return self.verdict == "block"

    @property
    def warns_spend(self) -> bool:
        return self.verdict == "warn"

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovalDecision:
    action: str
    request_id: str
    reasons: List[str]
    requires_human_signature: bool = False
    screening: Optional[DestinationScreening] = None
    checked_at: str = field(default_factory=utc_now_iso)

    def to_json(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.screening:
            payload["screening"] = self.screening.to_json()
        return payload


@dataclass(frozen=True)
class Receipt:
    request_id: str
    tx_hash: str
    destination: str
    amount: Decimal
    token_symbol: str
    purpose: str
    recorded_at: str = field(default_factory=utc_now_iso)

    def to_json(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["amount"] = decimal_to_str(self.amount)
        return payload


@dataclass(frozen=True)
class BudgetSummary:
    agent_id: str
    chain_id: str
    token_symbol: str
    daily_limit: Decimal
    spent_today: Decimal
    remaining_today: Decimal
    receipt_count: int

    def to_json(self) -> Dict[str, Any]:
        payload = asdict(self)
        for key in ("daily_limit", "spent_today", "remaining_today"):
            payload[key] = decimal_to_str(payload[key])
        return payload
