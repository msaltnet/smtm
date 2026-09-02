---
status: active
version: 1.1
last-updated: 2026-09-01
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
- a live external side effect is required, except for the separately approved Issue mutation, Draft PR creation, and linked ClickUp completion after a confirmed PR merge;
- deployment, package publication, release, or other external publication is required;
- privacy, security, compliance, or legal judgment is required;
- verification remains unresolved after investigation;
- cleanup of a closed-unmerged PR worktree or a worktree with uncommitted changes is required.

Automatic merge, deployment, release, trading, and Issue closure are outside standing authorization.

**Done when:** automatic verification passes and a Draft PR is ready for user review.

**Output:** code, tests, required documentation, and Draft PR.

## 4. Manual QA, review, and merge

Use `$pr-qa` for an implemented Draft PR. The agent inspects the exact PR head and affected behavior, runs focused tests followed by `python -m pytest tests/unit_tests -q`, and records the verified head SHA. It then prepares a safe local or mocked manual QA entry point using fakes, mocks, or recorded data. An explicitly authorized sandbox may be used when necessary, but PR QA never reads `.env` values or places a real-money order.

Keep the PR in Draft and retain the local task branch and worktree while the user follows the change-specific QA steps. The agent addresses feedback on the same PR, repeats verification and safe QA preparation for the new head, and requests QA again.

An unambiguous `검수 완료` authorizes merge only for the exact tested head SHA. Immediately before merge, re-read the remote head, required CI, conflicts, review blocks, and branch protection. A changed head invalidates verification and QA. When every gate passes, merge using the repository's default allowed method and confirm the remote merged state before any cleanup.

QA approval does not authorize deployment, package publication, access to production credentials, live-account mutation, sandbox use that requires credentials, or live trading. Each remains a separate authorization boundary.

**Done when:** review evidence is recorded and the approved PR is merged.

**Output:** reviewed and merged PR.

## 5. Close and improve

Only after confirming the PR merge, close a linked Issue when the merged PR demonstrably satisfies it. If an explicit ClickUp task ID or URL is linked, mark only that task Complete. This is a one-way completion follow-up, not GitHub synchronization. When no link is provided, do not search for, create, or infer one. A failed ClickUp update does not block GitHub completion or local cleanup. If the response is uncertain, read the current task status before any retry and report the result without making a duplicate mutation.

Update the local base branch from its remote, then verify the task worktree is clean before removing it and deleting the local feature branch. Preserve an unmerged, closed-without-merge, or dirty worktree and branch and request an explicit cleanup decision.

Connect the PR and Issue, confirm required source-of-truth documentation was included in the merged PR, and separate out-of-scope work into follow-up candidates. Missing documentation becomes a proposed follow-up rather than a direct edit to the base branch.

Record workflow friction when it materially delays or weakens a task. Review accumulated candidates every five completed Issues and adopt only repeated or high-impact improvements.

**Done when:** Issue, PR, documentation, and remaining work have clear states.

## Required user involvement

Routine work has two approval points:

1. exact implementation-ready Issue draft and repository;
2. Draft PR manual QA and merge.

All other routine technical decisions belong to the agent. Only the explicit stop conditions above require intermediate user input.
