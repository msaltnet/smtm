---
name: Implementation-ready change
about: A researched feature, bug fix, or trading-safety change ready for development
title: ""
labels: ""
assignees: ""
---

## Problem

Describe the observed user or system problem and its evidence. Distinguish verified incidents from hypotheses and requested capabilities.

## Goal

State the observable outcome after completion.

## Current behavior and evidence

Describe verified behavior from code, tests, documentation, supplied logs, or safe reproduction. Cite repository-relative files and symbols where useful.

## Required behavior

Describe the intended user and system behavior without unnecessary implementation prescription.

## Code and implementation investigation

- Relevant modules, files, symbols, tests, and existing patterns
- Runtime and state flow
- Related Issues or PRs and duplicate-search result
- Material compatibility, concurrency, migration, performance, security, and privacy constraints
- Verified facts, inferences, and recommendations clearly distinguished

## Trading and external-system impact

- Virtual trading
- Live exchange orders and account balances
- Credentials and secrets
- Persisted state or migration
- External APIs, rate limits, cost, deployment, or publication
- Safe validation using fakes, mocks, recorded data, or an explicitly authorized sandbox

## Recommended implementation

Explain the approach, architectural fit, and why meaningful alternatives were not selected.

## Scope

List affected components and data flows. Keep the work within one reviewable PR or propose separate follow-up Issues.

## Failure modes and edge cases

Cover applicable duplicates, retries, ambiguous exchange responses, concurrency, cancellation, restart, partial failure, offline behavior, and backward compatibility.

## Acceptance criteria

- [ ] Each criterion is an independently observable pass/fail result.
- [ ] Existing relevant behavior has regression protection.
- [ ] Real-money and credential boundaries are testable when applicable.

## Test plan

### Automated

Name test levels, behaviors, fakes or mocks, and commands.

### Manual QA

Give numbered actions and expected results. Default to virtual trading and never request production credentials.

## Documentation impact

Name README, `docs/public/`, release-note, or other files to update, or explain why none change.

## Out of scope

List adjacent work intentionally excluded.

## Risks and unresolved facts

List remaining risks and evidence still needed. Resolve blocking product decisions before marking the Issue ready.

## Source

Identify the direct request, report, existing Issue, or supplied evidence without copying secrets or personal data.
