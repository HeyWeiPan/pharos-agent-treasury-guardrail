---
name: pharos-agent-treasury-guardrail
description: Decides whether an autonomous Pharos spending workflow should approve, escalate, or block a proposed payment using treasury policy and destination screening.
version: 1.0.0
---

# Pharos Agent Treasury Guardrail Skill

## What It Does
This skill checks a proposed Pharos payment before an agent spends funds. It returns `approve`, `needs_human_approval`, or `block` based on treasury policy, destination screening, spending thresholds, and budget state.

Receipt and budget data are returned as structured objects so the caller decides how to persist audit information.

## When To Use / Triggers
- A workflow asks whether it can spend PHRS or another configured token.
- A proposed spend must be checked against daily and per-transaction limits.
- A destination must be screened before payment.
- A payment amount crosses the human approval threshold.
- A receipt or budget summary is needed after an approved transaction.

## Required Inputs
- `agent_id`: policy owner.
- `chain_id`: Pharos testnet is `688688`.
- `token_symbol`: token governed by the policy.
- `destination`: payment destination.
- `amount`: decimal string or exact decimal value.
- `purpose`: reason for the spend.
- `request_id`: stable idempotency key for the proposed spend.

## Policy Inputs
- `daily_limit`
- `per_tx_limit`
- `human_approval_threshold`
- optional allowed destinations
- optional blocked destinations
- optional destination screening
- `screening_block_level`
- `screening_warn_level`

## Workflow
1. Load or set the treasury policy for the spending workflow.
2. Normalize the destination address.
3. If destination screening is required, call the injected local screener.
4. Block if the chain, token, amount, destination, daily budget, or screening result violates policy.
5. Escalate to human approval when the destination is warning-level risk or the amount meets the configured approval threshold.
6. Approve only when policy and screening both pass.
7. Return a JSON-friendly decision object.
8. After execution, record a structured receipt through `record_receipt` and summarize budget with `summarize_budget`.

## Primitives / API
- `set_policy(policy: GuardrailPolicy) -> GuardrailPolicy`: stores and validates the spending policy for an agent.
- `check_spend(request: SpendRequest) -> ApprovalDecision`: dry-runs a proposed spend against policy and screening.
- `approve_or_block(request: SpendRequest) -> ApprovalDecision`: returns approve, needs_human_approval, or block.
- `record_receipt(receipt: Receipt) -> Receipt`: records an executed spend as structured in-memory data.
- `summarize_budget(agent_id: str) -> BudgetSummary`: returns current spend, remaining budget, and receipt count.

## Install & Run
Install locally:

```bash
pip install -e .
```

Run the local natural-language scenario demo:

```bash
python3 examples/agent_demo.py
```

Run the CLI demo:

```bash
treasury-guardrail demo
```

## Output
Return a JSON object containing:
- `action`: `approve`, `needs_human_approval`, or `block`
- `request_id`
- decision reasons
- whether a human signature is required
- optional destination screening result
- timestamp

## Security (CertiK-Clean)
- Destination screening is injected explicitly.
- Default demos are offline and deterministic.
- No shell execution.
- No hidden file writes.
- No broad network access.
- Receipt and audit data are returned as structured objects; callers decide persistence.

## Demo
- Agent-style scenario demo: `examples/agent_demo.py`.
- CLI demo and package details: `README.md`.
