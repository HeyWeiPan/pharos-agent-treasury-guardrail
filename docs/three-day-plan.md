# 3-Day Implementation Plan

## Day 1: Core Skill

- Lock public primitive names and JSON payloads.
- Implement policy validation, spend checks, approval decisions, receipt recording, and budget summary.
- Add deterministic pytest coverage for approve, block, human approval, duplicate receipt, and budget accounting.
- Keep destination screening as an interface that can consume the shared risk verdict.

Definition of done:

- `pytest` passes locally.
- `treasury-guardrail demo` returns readable JSON for approve, human-review, risk-review, and block paths.
- README explains scope, setup, and contract.

## Day 2: Skill Packaging + Demo Story

- Add the Pharos/Anvita package wrapper after the required schema is confirmed.
- Add MCP-style wrapper if no hard Pharos schema exists.
- Add `examples/demo_scenario.json` and a scriptable demo path for video recording.
- Add a short architecture diagram or flow section to README.

Definition of done:

- A reviewer can run the Skill from a clean clone.
- Demo script shows agent request -> guardrail decision -> receipt -> summary.
- Any chain/RPC dependency is optional or clearly mocked.

## Day 3: Differentiation + Submission Polish

- Plug in the shared destination screening rules at heuristic level:
  - explicit blocklist
  - allowlist
  - contract/external-account classification if RPC is ready
  - verified-source flag if explorer data is available
  - known-malicious-list hook if data is available
- Harden README for DoraHacks: problem, solution, reusable Skill API, demo, limitations.
- Record demo video and prepare submission text.

Definition of done:

- Core Skill remains complete even if screening data is unavailable.
- Differentiation layer is presented as safety screening, not full audit.
- Repo link, demo video, and submission notes are ready for handoff.
