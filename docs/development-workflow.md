---
status: active
version: 1.0
last-updated: 2026-08-30
review-cycle: every-5-completed-issues
---

# Development workflow

This is the source of truth for human-and-agent development in smtm. The user approves product intent and the final result; the agent owns repository investigation, implementation, verification, and handoff.

## 1. Capture an idea or problem

Direct conversation, a bug report, a feature request, or an existing GitHub Issue is sufficient input. The user identifies the desired outcome. Detailed implementation and test design are not required at this stage.

**Done when:** the input explains the proposal or observed problem well enough to begin repository research.

**Output:** direct request, report, or existing Issue reference.

## 2. Create or improve an implementation-ready Issue

Use `$smtm-issue`.

The agent identifies `msaltnet/smtm`, reads repository instructions, and investigates current code, tests, public documentation, and related Issues or PRs. The proposed Issue separates verified evidence, inference, and recommendation and defines scope, acceptance criteria, tests, documentation impact, and risks.

Virtual trading and real-money behavior must be distinguished. Classify effects on exchange requests, credentials, account balances, persistence, external APIs, cost, deployment, and publication. Issue preparation never reads secrets or places an order.

The user approves the exact final title, body, mutation type, and target repository. The agent then creates or updates exactly one Issue, verifies its URL, and stops.

**Done when:** an approved Issue URL contains enough evidence and detail for implementation without additional technical decisions.

**Output:** implementation-ready GitHub Issue.

## 3. Approved Issue: autonomous implementation

An approved Issue is standing authorization for routine, reversible investigation, design, planning, implementation, testing, refactoring, documentation changes, and Draft PR creation. Superpowers and other helper skills do not introduce additional design, plan, execution-mode, progress, or branch-finish approval questions.

When more than one implementation satisfies the Issue, choose the smallest and most reversible option supported by repository evidence. Record material assumptions, decisions, verification results, risks, and manual QA steps in the Draft PR.

The agent stops only when:

- acceptance criteria conflict and lead to materially different product behavior;
- credentials or authority are missing and no safe alternative exists;
- irreversible deletion or migration is required;
- a paid service or cost is required;
- Real-money trading, exchange-account mutation, or a live order is required;
- a live external side effect is required, except for the separately approved Issue mutation and Draft PR creation;
- deployment, package publication, release, or other external publication is required;
- privacy, security, compliance, or legal judgment is required;
- verification remains unresolved after investigation.

Automatic merge, deployment, release, trading, and Issue closure are outside standing authorization.

**Done when:** automatic verification passes and a Draft PR is ready for user review.

**Output:** code, tests, required documentation, and Draft PR.

## 4. Manual QA, review, and merge

The user follows the Draft PR's manual QA steps and evaluates product behavior, usability, and any environment-specific result. The agent addresses review feedback and re-runs verification. The user approves merge and any deployment, release, or live-system action separately.

**Done when:** review evidence is recorded and the approved PR is merged.

**Output:** reviewed and merged PR.

## 5. Close and improve

After merge approval, connect the PR and Issue, update source-of-truth documentation, and separate out-of-scope work into follow-up candidates. Close the Issue only when authorized and repository policy permits it.

Record workflow friction when it materially delays or weakens a task. Review accumulated candidates every five completed Issues and adopt only repeated or high-impact improvements.

**Done when:** Issue, PR, documentation, and remaining work have clear states.

## Required user involvement

Routine work has two approval points:

1. exact implementation-ready Issue draft and repository;
2. Draft PR manual QA and merge.

All other routine technical decisions belong to the agent. Only the explicit stop conditions above require intermediate user input.
