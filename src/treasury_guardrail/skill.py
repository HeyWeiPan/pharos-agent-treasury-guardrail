from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Protocol

from .types import (
    ApprovalDecision,
    BudgetSummary,
    DestinationScreening,
    GuardrailPolicy,
    Receipt,
    SpendRequest,
)


class DestinationScreener(Protocol):
    def screen(self, destination: str) -> DestinationScreening:
        ...


class PolicyDestinationScreener:
    def __init__(self, blocked_destinations: Optional[Iterable[str]] = None, warned_destinations: Optional[Iterable[str]] = None):
        self.blocked_destinations = {normalize_address(addr) for addr in (blocked_destinations or [])}
        self.warned_destinations = {normalize_address(addr) for addr in (warned_destinations or [])}

    def screen(self, destination: str) -> DestinationScreening:
        normalized = normalize_address(destination)
        if normalized in self.blocked_destinations:
            return DestinationScreening(
                destination=destination,
                verdict="block",
                risk_level="CRITICAL",
                confidence=1.0,
                reasons=["destination is explicitly blocked by policy"],
            )
        if normalized in self.warned_destinations:
            return DestinationScreening(
                destination=destination,
                verdict="warn",
                risk_level="HIGH",
                confidence=1.0,
                reasons=["destination requires human review by risk policy"],
            )
        return DestinationScreening(
            destination=destination,
            verdict="allow",
            risk_level="LOW",
            confidence=1.0,
            reasons=["destination passed policy screening"],
        )


class GuardrailSkill:
    """Reusable treasury guardrail skill.

    This in-memory implementation is the Phase 1 core. Persistence and Pharos-specific
    packaging can wrap this without changing the primitive contracts.
    """

    def __init__(self, screener: Optional[DestinationScreener] = None):
        self._policies: Dict[str, GuardrailPolicy] = {}
        self._receipts: List[Receipt] = []
        self._screener = screener

    def set_policy(self, policy: GuardrailPolicy) -> GuardrailPolicy:
        validate_policy(policy)
        self._policies[policy.agent_id] = policy
        return policy

    def check_spend(self, request: SpendRequest) -> ApprovalDecision:
        policy = self._require_policy(request.agent_id)
        reasons: List[str] = []
        screening = self._screen_if_needed(policy, request.destination)

        if policy.chain_id != request.chain_id:
            reasons.append("request chain_id does not match policy")
        if policy.token_symbol != request.token_symbol:
            reasons.append("request token_symbol does not match policy")
        if request.amount <= Decimal("0"):
            reasons.append("amount must be positive")
        if request.amount > policy.per_tx_limit:
            reasons.append("amount exceeds per-transaction limit")
        if normalize_address(request.destination) in normalized(policy.blocked_destinations):
            reasons.append("destination is blocked by policy")
        if policy.allowed_destinations and normalize_address(request.destination) not in normalized(policy.allowed_destinations):
            reasons.append("destination is not in policy allowlist")

        spent_today = self._spent_for_policy(policy)
        if spent_today + request.amount > policy.daily_limit:
            reasons.append("amount would exceed daily limit")
        if screening and screening.blocks_spend:
            reasons.append("destination screening blocked spend")

        if reasons:
            return ApprovalDecision(
                action="block",
                request_id=request.request_id,
                reasons=reasons,
                screening=screening,
            )

        if screening and screening.warns_spend:
            return ApprovalDecision(
                action="needs_human_approval",
                request_id=request.request_id,
                reasons=["destination screening requires human review"],
                requires_human_signature=True,
                screening=screening,
            )

        if request.amount >= policy.human_approval_threshold:
            return ApprovalDecision(
                action="needs_human_approval",
                request_id=request.request_id,
                reasons=["amount meets human approval threshold"],
                requires_human_signature=True,
                screening=screening,
            )

        return ApprovalDecision(
            action="approve",
            request_id=request.request_id,
            reasons=["within configured treasury policy"],
            screening=screening,
        )

    def approve_or_block(self, request: SpendRequest) -> ApprovalDecision:
        return self.check_spend(request)

    def record_receipt(self, receipt: Receipt) -> Receipt:
        policy = self._require_policy_by_receipt(receipt)
        if receipt.amount <= Decimal("0"):
            raise ValueError("receipt amount must be positive")
        if policy.token_symbol != receipt.token_symbol:
            raise ValueError("receipt token_symbol does not match policy")
        if self._receipt_exists(receipt.request_id):
            raise ValueError(f"receipt already recorded for request_id={receipt.request_id}")
        self._receipts.append(receipt)
        return receipt

    def summarize_budget(self, agent_id: str) -> BudgetSummary:
        policy = self._require_policy(agent_id)
        spent_today = self._spent_for_policy(policy)
        return BudgetSummary(
            agent_id=policy.agent_id,
            chain_id=policy.chain_id,
            token_symbol=policy.token_symbol,
            daily_limit=policy.daily_limit,
            spent_today=spent_today,
            remaining_today=max(Decimal("0"), policy.daily_limit - spent_today),
            receipt_count=sum(1 for receipt in self._receipts if receipt.token_symbol == policy.token_symbol),
        )

    def _screen_if_needed(self, policy: GuardrailPolicy, destination: str) -> Optional[DestinationScreening]:
        if not policy.require_destination_screening:
            return None
        screener = self._screener or PolicyDestinationScreener(policy.blocked_destinations)
        return apply_policy_thresholds(screener.screen(destination), policy)

    def _spent_for_policy(self, policy: GuardrailPolicy) -> Decimal:
        return sum(
            receipt.amount
            for receipt in self._receipts
            if receipt.token_symbol == policy.token_symbol
        )

    def _receipt_exists(self, request_id: str) -> bool:
        return any(receipt.request_id == request_id for receipt in self._receipts)

    def _require_policy(self, agent_id: str) -> GuardrailPolicy:
        try:
            return self._policies[agent_id]
        except KeyError as exc:
            raise ValueError(f"no policy configured for agent_id={agent_id}") from exc

    def _require_policy_by_receipt(self, receipt: Receipt) -> GuardrailPolicy:
        matching = [
            policy
            for policy in self._policies.values()
            if policy.token_symbol == receipt.token_symbol
        ]
        if not matching:
            raise ValueError(f"no policy configured for token_symbol={receipt.token_symbol}")
        return matching[0]


def validate_policy(policy: GuardrailPolicy) -> None:
    if policy.daily_limit <= Decimal("0"):
        raise ValueError("daily_limit must be positive")
    if policy.per_tx_limit <= Decimal("0"):
        raise ValueError("per_tx_limit must be positive")
    if policy.human_approval_threshold <= Decimal("0"):
        raise ValueError("human_approval_threshold must be positive")
    if policy.per_tx_limit > policy.daily_limit:
        raise ValueError("per_tx_limit cannot exceed daily_limit")
    validate_risk_level(policy.screening_block_level)
    validate_risk_level(policy.screening_warn_level)
    if RISK_LEVELS[policy.screening_warn_level] > RISK_LEVELS[policy.screening_block_level]:
        raise ValueError("screening_warn_level cannot be stricter than screening_block_level")


RISK_LEVELS = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}


def apply_policy_thresholds(screening: DestinationScreening, policy: GuardrailPolicy) -> DestinationScreening:
    validate_risk_level(screening.risk_level)
    risk_value = RISK_LEVELS[screening.risk_level]
    if risk_value >= RISK_LEVELS[policy.screening_block_level]:
        verdict = "block"
    elif risk_value >= RISK_LEVELS[policy.screening_warn_level]:
        verdict = "warn"
    else:
        verdict = "allow"
    return replace(screening, verdict=verdict)


def validate_risk_level(level: str) -> None:
    if level not in RISK_LEVELS:
        raise ValueError(f"unsupported risk level: {level}")


def normalize_address(address: str) -> str:
    return address.strip().lower()


def normalized(addresses: Iterable[str]) -> set:
    return {normalize_address(address) for address in addresses}
