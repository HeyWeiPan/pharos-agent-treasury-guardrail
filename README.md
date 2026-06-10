# Pharos Agent Treasury Guardrail

Reusable skill for agents that need to spend safely on Pharos.

The skill sits before payment, trading, or delegation agents and answers a simple question:
can this agent spend this amount to this destination right now?

## Phase 1 Scope

Core primitives:

- `set_policy`: configure budget limits, allowlists, blocklists, and human approval threshold.
- `check_spend`: dry-run a spend request against policy.
- `approve_or_block`: return one of `approve`, `needs_human_approval`, or `block`.
- `record_receipt`: record an executed transaction for audit and budget tracking.
- `summarize_budget`: return current spend and remaining budget.

Optional differentiation layer:

- `screen_destination`: plug in a shared risk memo verdict from a diligence engine. The policy maps risk levels to allow, warn, or block.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
treasury-guardrail demo
```

Without installing:

```bash
PYTHONPATH=src python3 -m treasury_guardrail.cli demo
```

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
  "chain_id": "688688",
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

The current implementation is dependency-light and in-memory so it can be wrapped by a specific hackathon skill schema later. Receipt and audit data are returned as structured objects; the package does not write audit files by itself.

Likely adapters:

- CLI wrapper for DoraHacks demo video.
- MCP-style tool wrapper exposing the five primitives to an agent.
- Pharos package/schema wrapper once requirements are known.
- Destination screening adapter supplied by the shared RWA risk diligence core.
