# Repository instructions

## Project

- smtm is a Python 3.9+ autonomous cryptocurrency trading system controlled through Telegram.
- Preserve the separation `SystemOperator -> SessionManager -> TradingOperator -> Strategy -> SafetyGuard -> Trader`.
- Run focused tests first, then `python -m pytest tests/unit_tests -q`. Integration tests require external credentials and are not a default verification step.
- Never read or print `.env` values, API keys, Telegram tokens, account data, or other secrets.
- Use fakes, mocks, recorded data, or an explicitly authorized sandbox. Never place a real-money order merely to reproduce or verify a change.

## Development workflow

- `docs/development-workflow.md` is the source of truth when this repository is opened independently.
- Use `$smtm-issue` when a direct request, feature idea, bug report, trading-safety concern, or sparse Issue needs to become an implementation-ready GitHub Issue.
- Before creating or updating an Issue, research the applicable code, tests, public documentation, and related Issues or PRs. Show the exact final title, body, mutation type, and target repository for user approval.
- An approved GitHub Issue is standing authorization for routine, reversible investigation, design, planning, implementation, testing, refactoring, documentation, and Draft PR creation.
- Superpowers and other helper skills do not add routine approval gates: do not ask again for design approval, plan approval, execution mode, progress confirmation, or branch-finish options. Choose the smallest, most reversible evidence-backed option and record important assumptions and decisions in the Draft PR.
- The Draft PR is the only routine development approval gate. Stop only for conflicting acceptance criteria with materially different product outcomes, missing authority or credentials without a safe alternative, irreversible data changes, cost, real-money order or live-account action, live external side effects outside the separately approved Issue mutation, Draft PR creation, and linked ClickUp completion after a confirmed PR merge, external publication, privacy/security/legal judgment, unresolved verification failure after investigation, or cleanup of a closed-unmerged or dirty task worktree.
- Use `$pr-qa` for implemented Draft PR verification, safe local QA preparation, user QA iteration, merge, and post-merge cleanup.
- For smtm, PR QA uses focused tests, `python -m pytest tests/unit_tests -q`, fakes, mocks, recorded data, or an explicitly authorized sandbox. It never reads `.env` values or places a real-money order.
- User QA completion authorizes the repository's default allowed merge method only for the tested PR head SHA. Re-read the remote head, required CI, conflicts, and review blocks immediately before merge; a changed head requires verification and QA again.
- QA approval does not authorize deployment, package publication, production credentials, live-account mutation, or trading.
- After confirmed merge, close a satisfied linked Issue, complete only an explicitly linked ClickUp Task, and remove only a clean merged worktree and local feature branch. Preserve unmerged or dirty workspaces.

The `검수 완료` gate applies only to the exact tested SHA.
