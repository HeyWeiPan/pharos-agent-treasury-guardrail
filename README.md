# Pharos Skill Engine Treasury Guardrail

Reusable guardrail for agents that use the official
`PharosNetwork/pharos-skill-engine` to spend safely on Pharos.

The official Skill Engine provides the raw Pharos execution layer: balance
queries, token queries, gas estimation, native transfers, ERC20 writes, contract
write calls, deployment, verification, airdrops, and script generation through
`cast` / `forge`.

This skill sits in front of that execution layer and answers a different
question:

can this agent run the planned Skill Engine transaction right now?

It is a policy gate, not a replacement for the Skill Engine command references.
From the user's perspective, this skill should guide the agent to use the
official Skill Engine automatically; the user should not need to manually tell
the agent to run Skill Engine first.

## Phase 1 Scope

Core primitives:

- `set_policy`: configure budget limits, allowlists, blocklists, and human approval threshold.
- `check_spend`: dry-run a spend request against policy.
- `approve_or_block`: return one of `approve`, `needs_human_approval`, or `block`.
- `record_receipt`: record an executed transaction for audit and budget tracking.
- `summarize_budget`: return current spend and remaining budget.

Optional differentiation layer:

- `screen_destination`: plug in a shared risk memo verdict from a diligence engine. The policy maps risk levels to allow, warn, or block.

## Pharos Skill Engine Integration

This package depends on `PharosNetwork/pharos-skill-engine` as its execution
layer. When an agent receives a Pharos payment or transaction request through
this guardrail, it should automatically load or clone the official Skill Engine
and then follow this sequence:

1. Bootstrap the official Skill Engine if it is not already present:
   `treasury-guardrail bootstrap-skill-engine`.
2. Use Skill Engine `assets/networks.json` to resolve the target network.
3. Use Skill Engine `assets/tokens.json` for known token symbols and addresses.
4. Use Skill Engine `references/query.md` to check balances, token metadata, and contract state.
5. Build a spend request for this guardrail.
6. Call `approve_or_block`.
7. If the decision is `approve`, continue to Skill Engine `references/transaction.md` for gas estimation and transaction sending.
8. If the decision is `needs_human_approval`, stop and request human approval before sending.
9. If the decision is `block`, do not send the transaction.
10. After a successful Skill Engine transaction, call `record_receipt` and `summarize_budget`.

See `references/treasury-guardrail.md` for the full agent workflow.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
treasury-guardrail bootstrap-skill-engine
pytest
treasury-guardrail demo
```

Without installing:

```bash
PYTHONPATH=src python3 -m treasury_guardrail.cli demo
```

The bootstrap command installs `PharosNetwork/pharos-skill-engine` into
`vendor/pharos-skill-engine`, so users only install and invoke this guardrail
skill.

## Demo Output

The demo shows three spend paths:

- small spend: approved automatically
- larger spend: escalated for human approval
- blocked destination: rejected by policy and screening
- high-risk destination: escalated or blocked according to policy thresholds

## Skill Contract

All primitives are JSON-friendly. Amounts are decimal strings to avoid float rounding.

Example policy:

```json
{
  "agent_id": "research-agent",
  "chain_id": "688689",
  "token_symbol": "PHRS",
  "daily_limit": "100",
  "per_tx_limit": "25",
  "human_approval_threshold": "10",
  "allowed_destinations": ["0x1111111111111111111111111111111111111111"],
  "blocked_destinations": [],
  "require_destination_screening": true,
  "screening_block_level": "CRITICAL",
  "screening_warn_level": "HIGH"
}
```

Example decision:

```json
{
  "action": "needs_human_approval",
  "request_id": "req-002",
  "reasons": ["amount meets human approval threshold"],
  "requires_human_signature": true
}
```

## Integration Notes

The current implementation is dependency-light and in-memory so it can be wrapped by the official Pharos Skill Engine flow. Receipt and audit data are returned as structured objects; the package does not write audit files by itself.

Likely adapters:

- Skill Engine pre-flight wrapper before `cast send` / contract write operations.
- CLI wrapper for DoraHacks demo video.
- MCP-style tool wrapper exposing the guardrail primitives to an agent.
- Destination screening adapter supplied by the shared RWA risk diligence core.
