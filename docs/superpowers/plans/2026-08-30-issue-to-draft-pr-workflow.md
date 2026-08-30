# Issue-to-Draft-PR Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested `smtm-issue` shared skill and a repository-local autonomous Issue-to-Draft-PR workflow to smtm.

**Architecture:** `my-skills` owns the reusable Issue investigation skill. smtm pins that repository as `.agents/skills` and owns its project-specific workflow, safety boundaries, Issue template, README links, and contract test.

**Tech Stack:** Agent Skills Markdown, Git submodules, Python 3.9+, pytest, GitHub Issue templates.

**Spec:** `docs/superpowers/specs/2026-08-30-issue-to-draft-pr-workflow-design.md`

## Global Constraints

- Exact final Issue body and target repository require user approval immediately before one Issue create or update mutation.
- Approved Issues authorize reversible work through Draft PR without routine intermediate approval questions.
- Real-money trading, credentials, irreversible data changes, costs, publication, merge, deployment, release, and Issue closure remain outside standing authorization.
- `my-skills` is pushed; smtm is committed locally on `master` and is not pushed.

---

### Task 1: Baseline the Issue-authoring behavior

**Files:**
- Create: temporary evaluator prompts outside both Git working trees
- Inspect: `smtm/`, `tests/`, `docs/public/`, `.github/`

**Interfaces:**
- Consumes: the design's Issue-preparation and safety requirements
- Produces: observed baseline failures that the skill must correct

- [ ] Run independent agents without `smtm-issue` against a sparse feature request, a real-trading bug report, and an urgent existing-Issue rewrite.
- [ ] Record whether each agent investigates code, distinguishes virtual and real trading, shows the exact draft, requests approval immediately before mutation, limits mutation to one Issue, and stops before implementation.
- [ ] Convert each observed failure into a required skill instruction; do not add rules unsupported by an observed failure or the design's safety boundary.

### Task 2: Create and validate `smtm-issue`

**Files:**
- Create: `my-skills/smtm-issue/SKILL.md`
- Create: `my-skills/smtm-issue/references/issue-contract.md`
- Modify: `my-skills/README.md`

**Interfaces:**
- Consumes: Task 1 failure evidence and smtm repository structure
- Produces: a discoverable skill that drafts one implementation-ready Issue and stops after URL verification

- [ ] Write the minimal skill instructions that correct the observed baseline failures and route the final body through `references/issue-contract.md`.
- [ ] Run the same independent scenarios with the skill present and verify all required behaviors.
- [ ] Run a separate adversarial scenario combining urgency, authority pressure, a request to place a real order, and a request to implement immediately; close only demonstrated loopholes.
- [ ] Run `quick_validate.py` against `smtm-issue` and `git diff --check` in `my-skills`.
- [ ] Commit `my-skills`, set its remote to `git@github.com:msaltnet/my-skills.git`, push `master`, and capture the 40-character commit SHA.

### Task 3: Add the repository workflow contract

**Files:**
- Create: `AGENTS.md`
- Create: `docs/development-workflow.md`
- Create: `.github/ISSUE_TEMPLATE/implementation.md`
- Create: `tests/unit_tests/test_development_workflow_contract.py`
- Modify: `README.md`
- Modify: `README-ko-kr.md`
- Create: `.gitmodules`
- Create: `.agents/skills` gitlink

**Interfaces:**
- Consumes: the pushed `my-skills` SHA from Task 2
- Produces: an independently discoverable autonomous workflow pinned to the tested skill

- [ ] Write the failing pytest contract first; require the skill path, approved-Issue standing authorization, no routine approval questions, Draft PR gate, real-trading stop boundary, and no automatic merge/deploy/release.
- [ ] Run `python -m pytest tests/unit_tests/test_development_workflow_contract.py -q` and confirm failure because the workflow files do not exist.
- [ ] Add `AGENTS.md`, the workflow, Issue template, and bilingual README links with the exact design boundaries.
- [ ] Register `git@github.com:msaltnet/my-skills.git` at `.agents/skills` and pin it to the tested SHA.
- [ ] Re-run the contract test and confirm it passes.

### Task 4: Verify and integrate smtm

**Files:**
- Verify: every file from Task 3
- Commit: the complete smtm workflow change

**Interfaces:**
- Consumes: the repository contract and pinned shared skill
- Produces: one verified smtm commit ready for local `master`

- [ ] Run `python -m pytest tests/unit_tests/test_development_workflow_contract.py -q`.
- [ ] Run `python -m pytest tests/unit_tests -q` using the repository virtual environment when available.
- [ ] Run `python -m black --check tests/unit_tests/test_development_workflow_contract.py` and `git diff --check`.
- [ ] Confirm `smtm-issue` resolves at `.agents/skills/smtm-issue/SKILL.md` and recursive submodule status succeeds.
- [ ] Request an independent review of requirements, diffs, safety boundaries, and unintended repository changes; fix Critical and Important findings.
- [ ] Commit the isolated smtm clone, then fetch and cherry-pick that commit into `C:\01_Code\smtm` after confirming the original remains clean and at the expected base commit.
- [ ] Re-run the contract test, recursive submodule status, and clean-status checks in the original repository without pushing smtm.
