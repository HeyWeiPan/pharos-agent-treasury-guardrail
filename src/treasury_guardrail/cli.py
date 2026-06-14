from __future__ import annotations

import argparse
import json
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

from .skill import GuardrailSkill, PolicyDestinationScreener
from .types import GuardrailPolicy, Receipt, SpendRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Treasury Guardrail Skill demo CLI")
    subcommands = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subcommands.add_parser(
        "bootstrap-skill-engine",
        help="Install the official Pharos Skill Engine dependency",
    )
    bootstrap_parser.add_argument(
        "--dest",
        default="vendor/pharos-skill-engine",
        help="Destination directory for PharosNetwork/pharos-skill-engine",
    )

    demo_parser = subcommands.add_parser("demo", help="Run the built-in demo scenario")
    demo_parser.add_argument("--chain-id", default="688689")
    demo_parser.add_argument("--token", default="PHRS")

    args = parser.parse_args()
    if args.command == "bootstrap-skill-engine":
        print_json(bootstrap_skill_engine(Path(args.dest)))
    elif args.command == "demo":
        print_json(run_demo(args.chain_id, args.token))


def bootstrap_skill_engine(dest: Path) -> dict[str, str]:
    repo = "https://github.com/PharosNetwork/pharos-skill-engine.git"
    if dest.exists():
        return {
            "status": "already_installed",
            "path": str(dest),
            "repo": repo,
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", repo, str(dest)],
        check=True,
    )
    return {
        "status": "installed",
        "path": str(dest),
        "repo": repo,
    }


def run_demo(chain_id: str, token_symbol: str) -> Any:
    high_risk_destination = "0x2222222222222222222222222222222222222222"
    blocked_destination = "0xdead000000000000000000000000000000000000"
    skill = GuardrailSkill(
        screener=PolicyDestinationScreener(
            blocked_destinations=[blocked_destination],
            warned_destinations=[high_risk_destination],
        )
    )
    policy = skill.set_policy(
        GuardrailPolicy(
            agent_id="demo-agent",
            chain_id=chain_id,
            token_symbol=token_symbol,
            daily_limit=Decimal("100"),
            per_tx_limit=Decimal("25"),
            human_approval_threshold=Decimal("10"),
            allowed_destinations=["0x1111111111111111111111111111111111111111", high_risk_destination],
            blocked_destinations=[blocked_destination],
            require_destination_screening=True,
        )
    )
    small_request = SpendRequest(
        agent_id="demo-agent",
        chain_id=chain_id,
        token_symbol=token_symbol,
        destination="0x1111111111111111111111111111111111111111",
        amount=Decimal("5"),
        purpose="buy dataset access for analysis agent",
        request_id="req-demo-001",
    )
    large_request = SpendRequest(
        agent_id="demo-agent",
        chain_id=chain_id,
        token_symbol=token_symbol,
        destination="0x1111111111111111111111111111111111111111",
        amount=Decimal("15"),
        purpose="pay external research agent",
        request_id="req-demo-002",
    )
    high_risk_request = SpendRequest(
        agent_id="demo-agent",
        chain_id=chain_id,
        token_symbol=token_symbol,
        destination=high_risk_destination,
        amount=Decimal("2"),
        purpose="pay newly discovered destination",
        request_id="req-demo-003",
    )
    blocked_request = SpendRequest(
        agent_id="demo-agent",
        chain_id=chain_id,
        token_symbol=token_symbol,
        destination=blocked_destination,
        amount=Decimal("1"),
        purpose="suspicious transfer",
        request_id="req-demo-004",
    )
    receipt = skill.record_receipt(
        Receipt(
            request_id=small_request.request_id,
            tx_hash="0xabc123",
            destination=small_request.destination,
            amount=small_request.amount,
            token_symbol=token_symbol,
            purpose=small_request.purpose,
        )
    )

    return {
        "policy": policy.to_json(),
        "small_spend": skill.approve_or_block(small_request).to_json(),
        "large_spend": skill.approve_or_block(large_request).to_json(),
        "high_risk_spend": skill.approve_or_block(high_risk_request).to_json(),
        "blocked_spend": skill.approve_or_block(blocked_request).to_json(),
        "receipt": receipt.to_json(),
        "summary": skill.summarize_budget("demo-agent").to_json(),
    }


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
