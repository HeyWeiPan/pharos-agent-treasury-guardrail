---
name: pharos-skill-engine-treasury-guardrail
description: Pre-flight policy gate for Pharos Skill Engine transactions. Use before a Pharos agent runs balance, gas estimate, native transfer, ERC20 transfer, airdrop, or contract write commands.
version: 1.0.0
---

# Pharos Skill Engine Treasury Guardrail Skill

## What It Does
This skill sits in front of the official `PharosNetwork/pharos-skill-engine` transaction flow. The Skill Engine knows how to query balances, estimate gas, send native transfers, call contract write methods, deploy contracts, run airdrops, and generate scripts. This guardrail decides whether an autonomous agent is allowed to proceed with those Skill Engine operations.

Use it as the pre-flight policy layer before the agent follows Skill Engine `references/transaction.md` or any write-capable workflow. It returns `approve`, `needs_human_approval`, or `block` based on treasury policy, destination screening, spending thresholds, and budget state.

Receipt and budget data are returned as structured objects so the caller decides how to persist audit information.

## Pharos Skill Engine Alignment
This skill composes with the official Pharos Skill Engine rather than duplicating its raw `cast` / `forge` commands.

- Treat `PharosNetwork/pharos-skill-engine` as a required execution dependency.
- If the official Skill Engine is not already present in this skill's dependency directory, run `treasury-guardrail bootstrap-skill-engine` before handling Pharos transaction requests.
- Read the official Skill Engine `SKILL.md` first for Pharos network configuration and command references.
- Use Skill Engine `assets/networks.json` for Atlantic testnet and mainnet metadata.
- Use Skill Engine `assets/tokens.json` for known token symbols and contract addresses.
- Use Skill Engine `references/query.md` for balance, token, transaction, and read-only contract checks.
- Call this guardrail before any Skill Engine transaction command from `references/transaction.md`.
- Continue to Skill Engine `cast estimate` / `cast send` only when this guardrail returns `approve`.
- Stop and ask for human confirmation when this guardrail returns `needs_human_approval`.
- Do not send the transaction when this guardrail returns `block`.
- After a successful transaction, call `record_receipt` and `summarize_budget` to update the treasury view.

## Dependency Bootstrap
The user should not need to manually orchestrate two separate skills. When this guardrail receives a Pharos payment, transfer, airdrop, or contract-write request, the agent must bootstrap the official Skill Engine automatically:

1. Check whether `vendor/pharos-skill-engine` already exists.
2. If missing, run `treasury-guardrail bootstrap-skill-engine` to install `PharosNetwork/pharos-skill-engine` into this skill's dependency directory.
3. If network access is unavailable, ask the user to provide the official package or repo path.
4. Read `vendor/pharos-skill-engine/SKILL.md` and matching reference files as this skill's execution manual.
5. Continue with this guardrail's policy workflow before any write operation.

## Capability Index
Load the matching section or primitive based on the user's intent.

| User Need | Capability | Detailed Instructions |
|-----------|------------|----------------------|
| Decide whether a Pharos Skill Engine transaction can proceed | `approve_or_block` | -> `references/treasury-guardrail.md#pre-flight-approval-before-skill-engine-transaction` |
| Dry-run a proposed payment against treasury limits | `check_spend` | -> `references/treasury-guardrail.md#dry-run-spend-check` |
| Configure agent budget, token, destination, and approval policy | `set_policy` | -> `references/treasury-guardrail.md#set-agent-treasury-policy` |
| Screen a destination before payment or contract write | destination screening adapter | -> `references/treasury-guardrail.md#destination-screening` |
| Record a completed Skill Engine transaction receipt | `record_receipt` | -> `references/treasury-guardrail.md#record-skill-engine-transaction-receipt` |
| Summarize spend, remaining budget, and receipt count | `summarize_budget` | -> `references/treasury-guardrail.md#summarize-agent-budget` |

## When To Use / Triggers
- A workflow asks whether it can spend PHRS, PROS, or another configured token.
- An agent is about to run Skill Engine `cast send`, ERC20 `transfer`, contract write call, or airdrop.
- An agent has used Skill Engine `query.md` / `transaction.md` to gather balance and gas context and needs a policy decision.
- A proposed spend must be checked against daily and per-transaction limits.
- A destination must be screened before payment.
- A payment amount crosses the human approval threshold.
- A receipt or budget summary is needed after an approved transaction.

## Required Inputs
- `agent_id`: policy owner.
- `chain_id`: Pharos Atlantic testnet is `688689`; Pharos mainnet is `1672`.
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
1. Auto-bootstrap the official Skill Engine with `treasury-guardrail bootstrap-skill-engine` if it is not already available.
2. Read official Skill Engine `assets/networks.json` and resolve the target network.
3. Use Skill Engine `references/query.md` to check sender balance, token metadata, and destination/contract state as needed.
4. Build a `SpendRequest` from the planned Skill Engine operation: sender agent, chain ID, token symbol, destination, amount, purpose, and request ID.
5. If destination screening is required, call the injected local screener.
6. Block if the chain, token, amount, destination, daily budget, or screening result violates policy.
7. Escalate to human approval when the destination is warning-level risk or the amount meets the configured approval threshold.
8. Approve only when policy and screening both pass.
9. If approved, continue to Skill Engine `references/transaction.md` for gas estimation and transaction sending.
10. After execution, record a structured receipt through `record_receipt` and summarize budget with `summarize_budget`.

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

Install the official Pharos Skill Engine dependency used by this guardrail:

```bash
treasury-guardrail bootstrap-skill-engine
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
- No hidden shell execution in the guardrail decision path.
- `bootstrap-skill-engine` is an explicit install command that clones the official dependency into `vendor/`.
- No hidden file writes.
- No broad network access.
- Receipt and audit data are returned as structured objects; callers decide persistence.

## Demo
- Agent-style scenario demo: `examples/agent_demo.py`.
- CLI demo and package details: `README.md`.
