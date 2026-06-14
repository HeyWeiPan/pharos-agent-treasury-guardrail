# Treasury Guardrail Reference

This reference teaches an agent how to place a treasury policy gate in front of
the official Pharos Skill Engine transaction flow.

The official Skill Engine owns raw Pharos operations:

- `references/query.md`: balance, token, transaction, and contract-read checks
- `references/transaction.md`: gas estimation, native transfers, ERC20 writes,
  contract writes, and airdrops
- `references/contract.md`: deploy and verify workflows
- `references/script-gen.md`: JS, TS, and Python interaction script generation
- `assets/networks.json`: Atlantic testnet and mainnet RPC, chain ID, explorer,
  and native token metadata
- `assets/tokens.json`: known token symbols and addresses

This guardrail owns the decision to proceed, stop for human approval, or block.
It does not replace the Skill Engine commands and does not execute shell
commands internally.

The agent should not ask the user to coordinate two separate skills. When the
user invokes this guardrail for a Pharos payment or transaction request, this
guardrail instructs the agent to bootstrap and read the official Skill Engine as
its execution manual.

## Bootstrap Official Skill Engine

### Agent Steps

1. Check whether `PharosNetwork/pharos-skill-engine` is already installed or
   available in the current workspace.
2. If it is missing and network access is available, run this skill's bootstrap
   command:

   ```bash
   treasury-guardrail bootstrap-skill-engine
   ```

   By default this installs the official repo into `vendor/pharos-skill-engine`.
3. If network access is unavailable, ask the user to provide the official Skill
   Engine package or repo path.
4. Read `vendor/pharos-skill-engine/SKILL.md`.
5. Use its `assets/` and `references/` files as the execution layer for the
   rest of this guardrail workflow.

### Rule

Do not require the user to say "use Skill Engine first." This guardrail is
responsible for invoking Skill Engine instructions whenever the request involves
Pharos balances, transfers, airdrops, or contract writes.

## Pre-flight Approval Before Skill Engine Transaction

Use this flow before any Skill Engine write operation, including native PHRS or
PROS transfers, ERC20 `transfer` / `approve`, contract write calls, deployments,
and airdrops.

### Agent Steps

1. Run `treasury-guardrail bootstrap-skill-engine` if the official Skill Engine
   is not already available.
2. Read the official Skill Engine `SKILL.md`.
3. Read Skill Engine `assets/networks.json` and resolve the target network.
4. Use Skill Engine `references/query.md` to check sender balance and token
   metadata when needed.
5. Use Skill Engine `references/transaction.md#gas-estimation` to estimate gas
   before final approval if the transaction shape is already known.
6. Build a spend request:
   - `agent_id`: policy owner or autonomous agent name
   - `chain_id`: target Pharos chain ID
   - `token_symbol`: native or ERC20 symbol
   - `destination`: payment recipient or contract address
   - `amount`: decimal string for the planned value transfer or budgeted spend
   - `purpose`: human-readable reason for the operation
   - `request_id`: stable idempotency key
7. Call `approve_or_block(request)`.
8. Branch on the decision:
   - `approve`: continue to Skill Engine `cast estimate` / `cast send` after
     normal account and network confirmation.
   - `needs_human_approval`: stop before `cast send` and ask the human to
     approve the exact destination, amount, network, and purpose.
   - `block`: do not execute the transaction.
9. After a successful Skill Engine transaction, call `record_receipt` and then
   `summarize_budget`.

### Output Parsing

The approval decision is JSON-friendly:

| Field | Meaning |
|-------|---------|
| `action` | `approve`, `needs_human_approval`, or `block` |
| `request_id` | Idempotency key from the spend request |
| `reasons` | Policy and screening reasons for the decision |
| `requires_human_signature` | Boolean escalation flag |
| `screening` | Optional destination risk result |
| `timestamp` | Decision timestamp |

### Error Handling

| Error | Handling |
|-------|----------|
| Missing policy | Ask the user to configure `set_policy` before spending |
| Unknown chain or token | Stop and ask for the intended Pharos network/token |
| Invalid destination | Stop before Skill Engine transaction commands |
| Daily limit exceeded | Return `block`; do not send |
| Human threshold reached | Return `needs_human_approval`; wait for approval |
| Destination screen is critical | Return `block`; do not send |

## Dry-run Spend Check

Use `check_spend(request)` when the user wants to preview a planned transaction
without authorizing execution.

### Agent Steps

1. Gather the same request fields used for pre-flight approval.
2. Call `check_spend(request)`.
3. Report the action and reasons.
4. Do not execute Skill Engine transaction commands from a dry run alone.

## Set Agent Treasury Policy

Use `set_policy(policy)` before the first spend request for an agent.

### Required Policy Fields

| Field | Meaning |
|-------|---------|
| `agent_id` | Agent or workflow owner |
| `chain_id` | Allowed Pharos chain |
| `token_symbol` | Governed token |
| `daily_limit` | Maximum daily spend |
| `per_tx_limit` | Maximum single-transaction spend |
| `human_approval_threshold` | Amount at or above which human approval is required |

### Optional Policy Fields

| Field | Meaning |
|-------|---------|
| `allowed_destinations` | Explicit destination allowlist |
| `blocked_destinations` | Explicit destination blocklist |
| `require_destination_screening` | Whether destination screening is mandatory |
| `screening_warn_level` | Risk level that escalates to human approval |
| `screening_block_level` | Risk level that blocks the transaction |

## Destination Screening

Destination screening can consume a risk memo from another skill, such as the
RWA risk due-diligence skill.

### Agent Steps

1. If a destination is a known contract or RWA token, run the destination risk
   skill first.
2. Convert its result to a screening verdict and risk level.
3. Pass that result into this guardrail before any Skill Engine write operation.

## Record Skill Engine Transaction Receipt

Use `record_receipt(receipt)` only after a Skill Engine transaction has
completed or failed with a transaction hash/status that should be tracked.

### Receipt Fields

| Field | Meaning |
|-------|---------|
| `request_id` | Original spend request ID |
| `tx_hash` | Skill Engine transaction hash |
| `status` | Transaction status |
| `amount` | Executed amount |
| `token_symbol` | Token spent |
| `destination` | Recipient or contract address |
| `purpose` | Original purpose |

## Summarize Agent Budget

Use `summarize_budget(agent_id)` after receipts are recorded or when the user
asks for remaining budget.

### Output

Return current spend, remaining daily budget, policy limits, and receipt count.

## Safety Rules

- Do not bypass this guardrail for Skill Engine write operations.
- Do not execute `cast send` when the guardrail returns `needs_human_approval`
  or `block`.
- Do not paste or print private keys.
- Do not move mainnet funds without explicit human confirmation.
- Keep this package dependency-light: Skill Engine executes commands; this
  guardrail decides whether those commands are allowed.
