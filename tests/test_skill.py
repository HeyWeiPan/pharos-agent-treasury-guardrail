from decimal import Decimal

import pytest

from treasury_guardrail import DestinationScreening, GuardrailPolicy, GuardrailSkill, Receipt, SpendRequest


ALLOWED = "0x1111111111111111111111111111111111111111"
BLOCKED = "0xdead000000000000000000000000000000000000"


@pytest.fixture()
def skill():
    guardrail = GuardrailSkill()
    guardrail.set_policy(
        GuardrailPolicy(
            agent_id="agent-1",
            chain_id="688688",
            token_symbol="PHRS",
            daily_limit=Decimal("100"),
            per_tx_limit=Decimal("25"),
            human_approval_threshold=Decimal("10"),
            allowed_destinations=[ALLOWED],
            blocked_destinations=[BLOCKED],
            require_destination_screening=True,
            screening_block_level="CRITICAL",
            screening_warn_level="HIGH",
        )
    )
    return guardrail


def spend(amount, destination=ALLOWED, request_id="req-1"):
    return SpendRequest(
        agent_id="agent-1",
        chain_id="688688",
        token_symbol="PHRS",
        destination=destination,
        amount=Decimal(amount),
        purpose="pay for agent tool access",
        request_id=request_id,
    )


def test_approves_small_allowed_spend(skill):
    decision = skill.approve_or_block(spend("5"))

    assert decision.action == "approve"
    assert decision.requires_human_signature is False
    assert decision.screening.verdict == "allow"


def test_escalates_at_human_approval_threshold(skill):
    decision = skill.approve_or_block(spend("10"))

    assert decision.action == "needs_human_approval"
    assert decision.requires_human_signature is True


def test_blocks_policy_and_screening_blocked_destination(skill):
    decision = skill.approve_or_block(spend("1", destination=BLOCKED))

    assert decision.action == "block"
    assert "destination is blocked by policy" in decision.reasons
    assert "destination screening blocked spend" in decision.reasons
    assert decision.screening.verdict == "block"


def test_warn_screening_escalates_to_human_approval():
    class WarnScreener:
        def screen(self, destination):
            return DestinationScreening(
                destination=destination,
                verdict="warn",
                risk_level="HIGH",
                confidence=0.8,
                reasons=["shared risk engine returned warn"],
            )

    guardrail = GuardrailSkill(screener=WarnScreener())
    guardrail.set_policy(
        GuardrailPolicy(
            agent_id="agent-1",
            chain_id="688688",
            token_symbol="PHRS",
            daily_limit=Decimal("100"),
            per_tx_limit=Decimal("25"),
            human_approval_threshold=Decimal("10"),
            allowed_destinations=[ALLOWED],
            require_destination_screening=True,
        )
    )

    decision = guardrail.approve_or_block(spend("1"))

    assert decision.action == "needs_human_approval"
    assert decision.requires_human_signature is True
    assert decision.screening.risk_level == "HIGH"


def test_policy_can_block_high_risk_destinations():
    class HighRiskScreener:
        def screen(self, destination):
            return DestinationScreening(
                destination=destination,
                verdict="warn",
                risk_level="HIGH",
                confidence=0.8,
                reasons=["shared risk engine returned high risk"],
            )

    guardrail = GuardrailSkill(screener=HighRiskScreener())
    guardrail.set_policy(
        GuardrailPolicy(
            agent_id="agent-1",
            chain_id="688688",
            token_symbol="PHRS",
            daily_limit=Decimal("100"),
            per_tx_limit=Decimal("25"),
            human_approval_threshold=Decimal("10"),
            allowed_destinations=[ALLOWED],
            require_destination_screening=True,
            screening_block_level="HIGH",
            screening_warn_level="MEDIUM",
        )
    )

    decision = guardrail.approve_or_block(spend("1"))

    assert decision.action == "block"
    assert decision.screening.verdict == "block"


def test_blocks_destination_outside_allowlist(skill):
    decision = skill.approve_or_block(spend("1", destination="0x2222222222222222222222222222222222222222"))

    assert decision.action == "block"
    assert "destination is not in policy allowlist" in decision.reasons


def test_blocks_when_daily_limit_would_be_exceeded(skill):
    skill.record_receipt(
        Receipt(
            request_id="req-existing",
            tx_hash="0xabc",
            destination=ALLOWED,
            amount=Decimal("90"),
            token_symbol="PHRS",
            purpose="previous spend",
        )
    )

    decision = skill.approve_or_block(spend("15", request_id="req-new"))

    assert decision.action == "block"
    assert "amount would exceed daily limit" in decision.reasons


def test_records_receipt_and_summarizes_budget(skill):
    skill.record_receipt(
        Receipt(
            request_id="req-1",
            tx_hash="0xabc",
            destination=ALLOWED,
            amount=Decimal("5"),
            token_symbol="PHRS",
            purpose="pay for agent tool access",
        )
    )

    summary = skill.summarize_budget("agent-1")

    assert summary.spent_today == Decimal("5")
    assert summary.remaining_today == Decimal("95")
    assert summary.receipt_count == 1


def test_rejects_duplicate_receipt(skill):
    receipt = Receipt(
        request_id="req-1",
        tx_hash="0xabc",
        destination=ALLOWED,
        amount=Decimal("5"),
        token_symbol="PHRS",
        purpose="pay for agent tool access",
    )
    skill.record_receipt(receipt)

    with pytest.raises(ValueError, match="receipt already recorded"):
        skill.record_receipt(receipt)
