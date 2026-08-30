# Issue-to-Draft-PR Workflow Design

## Goal

Give smtm a repository-local development contract that turns direct requests, feature ideas, bug reports, or sparse GitHub Issues into implementation-ready Issues, then lets an agent implement an approved Issue autonomously through a Draft PR.

## Sources of truth

- `AGENTS.md` contains the concise rules an agent must follow when the repository is opened independently.
- `docs/development-workflow.md` is the complete human-and-agent workflow.
- `.github/ISSUE_TEMPLATE/implementation.md` defines the minimum implementation-ready Issue contract.
- `.agents/skills/smtm-issue` supplies the reusable investigation and Issue-authoring procedure from `my-skills`.

The README files only link to the canonical workflow. They do not duplicate it.

## Issue preparation

`smtm-issue` accepts direct user input, feature requests, bug reports, and existing Issues. It identifies the smtm repository, reads its instructions, and investigates the current code, tests, public documentation, and related Issues or PRs. The final Issue draft separates verified facts from recommendations and includes scope, implementation detail, acceptance criteria, tests, documentation impact, and risk.

The skill distinguishes virtual trading from real trading. It explicitly identifies effects on exchange APIs, credentials, order placement, account balances, persistent state, and external services. It shows the exact final body and target repository immediately before requesting approval, creates or updates one Issue after approval, verifies the URL, and stops without implementing or mutating unrelated systems.

## Autonomous development

An approved GitHub Issue is standing authorization for routine, reversible investigation, design, planning, implementation, testing, refactoring, and documentation work through Draft PR creation. Superpowers or other helper skills must not introduce additional design, plan, execution-mode, progress, or branch-finish approval questions.

When multiple technical options satisfy the Issue, the agent selects the smallest and most reversible evidence-backed option. Important assumptions and decisions are recorded in the Draft PR. The Draft PR is the only routine development approval gate.

The agent stops only for:

- conflicting acceptance criteria that produce materially different product behavior;
- missing credentials or authority without a safe alternative;
- irreversible data deletion or migration;
- cost or paid-service use;
- real-money order execution or changes to live trading accounts;
- deployment, package publication, release, or other external publication;
- privacy, security, compliance, or legal judgment;
- verification failure that remains unresolved after investigation.

The standing authorization never includes automatic merge, deployment, release, real trading, or Issue closure.

## Repository integration

`my-skills` gains a top-level `smtm-issue/` skill with a concise entrypoint and an Issue contract reference. smtm registers `git@github.com:msaltnet/my-skills.git` at `.agents/skills`, pinned to the tested skill commit.

smtm adds:

- `AGENTS.md`
- `docs/development-workflow.md`
- `.github/ISSUE_TEMPLATE/implementation.md`
- `tests/unit_tests/test_development_workflow_contract.py`
- short links in `README.md` and `README-ko-kr.md`

The contract test verifies discovery of `smtm-issue`, standing approval through Draft PR, suppression of routine approval questions, real-trading safety boundaries, and the no-auto-merge/deploy/release rule.

## Validation and deployment

The new skill is tested with realistic pressure scenarios before and after the skill exists. Validation must demonstrate repository investigation, exact-draft approval, one-Issue mutation, real-trading risk classification, and stopping before implementation.

Run `quick_validate.py` for `smtm-issue`, the workflow contract test, smtm unit tests, formatting checks relevant to changed Python, and Git diff checks. Push only `my-skills`; apply the verified smtm commit to the local `master` without pushing it.
