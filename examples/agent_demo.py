from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from treasury_guardrail.skill import GuardrailSkill, PolicyDestinationScreener
from treasury_guardrail.types import GuardrailPolicy, SpendRequest


ALLOWED_DESTINATION = "0x1111111111111111111111111111111111111111"
HIGH_RISK_DESTINATION = "0x2222222222222222222222222222222222222222"
BLOCKED_DESTINATION = "0xdead000000000000000000000000000000000000"


SCENARIOS = [
    {
        "id": "small-vendor-payment",
        "request": "Can the agent pay 5 PHRS to the approved data vendor?",
        "destination": ALLOWED_DESTINATION,
        "amount": "5",
    },
    {
        "id": "approval-threshold-payment",
        "request": "Can the agent pay 15 PHRS to the approved research vendor?",
        "destination": ALLOWED_DESTINATION,
        "amount": "15",
    },
    {
        "id": "screened-high-risk-payment",
        "request": "Can the agent pay 2 PHRS to a destination marked high risk?",
        "destination": HIGH_RISK_DESTINATION,
        "amount": "2",
    },
    {
        "id": "blocked-destination-payment",
        "request": "Can the agent pay 1 PHRS to a blocked destination?",
        "destination": BLOCKED_DESTINATION,
        "amount": "1",
    },
]


def main() -> None:
    skill = GuardrailSkill(
        screener=PolicyDestinationScreener(
            blocked_destinations=[BLOCKED_DESTINATION],
            warned_destinations=[HIGH_RISK_DESTINATION],
        )
    )
    skill.set_policy(build_policy())
    print_json([run_scenario(skill, scenario) for scenario in SCENARIOS])


def build_policy() -> GuardrailPolicy:
    return GuardrailPolicy(
        agent_id="demo-agent",
        chain_id="688689",
        token_symbol="PHRS",
        daily_limit=Decimal("100"),
        per_tx_limit=Decimal("25"),
        human_approval_threshold=Decimal("10"),
        allowed_destinations=[ALLOWED_DESTINATION, HIGH_RISK_DESTINATION],
        blocked_destinations=[BLOCKED_DESTINATION],
        require_destination_screening=True,
        screening_block_level="CRITICAL",
        screening_warn_level="HIGH",
    )


def run_scenario(skill: GuardrailSkill, scenario: dict[str, str]) -> dict[str, Any]:
    request = SpendRequest(
        agent_id="demo-agent",
        chain_id="688689",
        token_symbol="PHRS",
        destination=scenario["destination"],
        amount=Decimal(scenario["amount"]),
        purpose=scenario["request"],
        request_id=f"req-{scenario['id']}",
    )
    decision = skill.approve_or_block(request)
    return {
        "scenario_id": scenario["id"],
        "request": scenario["request"],
        "triggered_skill": "treasury_guardrail",
        "primitive": "approve_or_block",
        "decision": decision.to_json(),
    }


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
