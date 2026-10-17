# Offline PAPER evaluation, version 1

This is a reproducible **plumbing evaluation**, not a comparison of real LLMs or
a claim about trading profitability. It runs the existing `StrategyBuyAndHold`
(BNH) and `StrategyLlm` against identical local snapshots, with separate real
`SimulationTrader` accounts. The LLM arm receives hand-authored fake responses.
No model, market-data provider, exchange, Telegram, account, or session is started.

## Run and inspect

From a repository checkout, Python 3.9+ and its standard library are sufficient:

```sh
python -S tools/evaluate_offline.py \
  --fixture tests/fixtures/evaluation/synthetic-smoke-v1.json \
  --output /tmp/smtm-evaluation.json
python -m json.tool /tmp/smtm-evaluation.json
```

Use a new output filename for each run; existing files are never overwritten.
`-S` demonstrates that no site packages, provider SDKs, or installed SMTM package
are needed. The command also works from another working directory when supplied
absolute script, fixture, and output paths. It does not require `.env`.
The output parent directory must already exist. A validation or file error
returns exit code 2; a complete report returns 0.

Run focused tests without installing dependencies:

```sh
python -S -m unittest tests.unit_tests.offline_evaluation_test -v
```

For the repository-wide suite, install the ordinary development dependencies in
your development environment and run `python -m pytest tests/unit_tests -q`.
Never use real credentials or integration tests merely to run this evaluation.

## Input contract

The supplied JSON fixture is a deliberately small synthetic scenario. To supply
locally recorded input, use the same structure and identify its source in
`provenance`; this command does not fetch or record market data for you.

Top-level required fields:

- `schema_version`: integer `1`
- `scenario_id`: nonempty identifier; version it when changing a scenario
- `data_kind`: `synthetic` or `recorded`
- `provenance`: nonempty description of where prices and scripted responses came from
- `currency`: one nonempty market/base-currency label, shared by all candles
- `initial_cash`, `min_order_value`: numeric values in `[1e-12, 1e15]`
- `ticks`: 1–10,000 ordered objects

Each tick contains:

- `at`: UTC time in exactly `YYYY-MM-DDTHH:MM:SS` format, strictly increasing
- `snapshot`: a complete list of typed objects; `[]` is explicitly missing data
- `scripted_llm`: one explicit script for that tick, even if it will be skipped

A snapshot permits zero or one `primary_candle`. Each primary candle needs
`market` equal to `currency`, `date_time` equal to `at`, and a numeric
`closing_price` in `[1e-12, 1e15]`. Other fields/items are retained in snapshot
hashes. Current strategies use only the primary candle. The fixture producer is
responsible for the point-in-time validity of recorded context; this harness
does not certify historical source timestamps, completeness or market realism.
At least one primary candle is required so final valuation has a price.

Supported scripts:

```json
{"kind": "decision", "decision": {"action": "buy", "price": 100, "amount": 2, "reason": "synthetic"}, "usage": {"input_tokens": 10, "output_tokens": 3}}
{"kind": "decision", "decision": {"action": "hold", "reason": "synthetic"}}
{"kind": "no_tool", "usage": {"input_tokens": 10, "output_tokens": 1}}
{"kind": "provider_error"}
```

`decision` must be an object but may intentionally contain invalid action,
price or amount values: the **real strategy** validates them, and the report
records the rejection. JSON NaN/Infinity are rejected anywhere. Usage is optional;
only nonnegative integer `input_tokens` and `output_tokens` are allowed. Booleans
are not counts. `provider_error` cannot contain usage because no response was
returned. Usage is scripted metadata, not a tokenizer estimate or observed bill.

## Time, order and comparison semantics

Each arm starts with the same initial cash, no holdings, fractional cash
accounting, zero fees and an independent simulator. Snapshot lists are deep
copied for each tick. Dictionary key ordering is canonicalized before replay,
because the existing LLM strategy renders candle dictionaries as text.

For each primary-candle tick:

1. Apply the current close as the simulator quote. Older pending orders can fill
   here; their callbacks update the strategy before its next decision.
2. Supply the snapshot to the strategy. No future snapshot is supplied.
3. Ask the strategy once for requests. The fake client returns that tick's script;
   it never advances a queue across missing-data ticks.
4. Submit requests unchanged to the simulator. Marketable limits can fill at the
   same observed close. This is an explicitly optimistic current-close execution
   assumption, not an executable next-tick backtest.
5. Record the account's cash, quantity and marked equity.

Missing-primary ticks skip quote updates and decisions in **both** arms, retaining
the last valuation. This evaluator policy prevents replaying a stale candle; it
does not change production behavior. At the end, cancel all pending orders and
mark remaining holdings at the last close. Do not liquidate them.

The BNH strategy's four-decimal sizing and the simulator's six-decimal holdings
remain intact. BNH can emit zero-sized requests when remaining cash is too small;
these simulator rejections are visible and are not silently treated as fills.
The `StrategyLlm` production prompt and validation are unchanged. Strategy files,
chat full-feed prompting, SafetyGuard, admission activation, runtime orchestration
and live order policies are outside this evaluation.

## Report contract

The output is strict JSON with `schema_version: 1` and
`evaluation_kind: "offline_scripted_plumbing"`.

- Scenario identity, data kind and provenance accompany the report.
- `fixture_sha256` hashes canonical semantic JSON. The CLI additionally records
  `fixture_file_sha256` for exact source bytes. Whitespace/key ordering can alter
  the latter without changing semantic outcomes.
- `source_sha256` contains exact SHA-256 values for the fixed production module
  subset and evaluator; `source_bundle_sha256` hashes that map. These identify
  the actual files, including local changes, rather than assuming a Git commit.
- `runtime` records Python version, platform and UTC creation time. `config`
  records cash, currency, minimum order, fees, accounting and execution/end policy.
- `limitations` travels with every artifact so detached results remain qualified.
- `arms` contains BNH and LLM results in that order.

Each arm includes ordered `ticks`, separate `finalization_events`, and `summary`.
Each tick records its index/time, full input snapshot hash, requests, emitted
simulator events, end-of-tick account, fake prompt hashes, returned scripted usage
and `local_decision_latency_ms`. Event `at`/`tick_index` identify **when the
callback happened**; `result.date_time` remains the original production order
submission time and must not be mistaken for a delayed fill's observation time.

Tick `outcome` is one of:

- `missing_primary_candle`: no quote update or decision
- `requests_emitted`: requests went to the simulator; inspect events for success,
  pending, cancellation or rejection (this does not itself mean a fill)
- `no_request`: baseline returned no request
- `hold`: scripted LLM explicitly chose hold
- `provider_error`: the fake raised the scripted provider exception
- `missing_decision_tool`: fake response had no tool call
- `decision_rejected`: a non-hold scripted decision produced no valid request

Summary definitions:

- `final_account.equity = cash + asset_amount * last_close`; reserved holdings
  are part of total holdings. Final pending orders have been canceled.
- `return_fraction = final_equity / initial_cash - 1`. This is unrealized plus
  realized change, with zero fees and no slippage; it is not annualized.
- `max_sampled_drawdown_fraction` is the maximum `(running_peak - equity) /
  running_peak` over initial cash and all end-of-tick equity samples. It does
  not measure intrabar drawdown or compare BNH and LLM execution quality.
- `filled_orders` counts terminal `done/success`; `failed_orders` counts
  terminal `failed`; `canceled_orders` counts terminal cancellations.
  `outcome_counts` counts decision outcomes separately.
- `scripted_token_totals` sums supplied counts. Missing keys contribute no known
  tokens; `usage_missing_call_count` counts calls without a complete returned
  input/output pair, including provider errors. A zero total is **not** proof of
  zero provider usage. `fake_call_count` is the actual local fake invocation count.
- `model_cost` is null because no model was used and no price configuration exists.
- Latency is measured with a monotonic clock around `strategy.get_request`,
  including local prompt construction, fake capture/hash work and validation.
  It excludes quote processing/fills. It is **not provider latency**, and the
  two arms' timing workloads differ. Null tick latency means no decision ran.

Repeat runs have identical decision, event, prompt-hash, account, token and outcome
semantics for the same semantic fixture/source/Python behavior. Runtime metadata
and measured latency are nondeterministic and must be excluded from equality
checks. Actual model comparisons require separately validated recorded inputs,
real provider usage/price evidence and an appropriate execution/cost model.

## Isolation and security boundary

The CLI imports only the standard library. A fixed allowlist loads existing
production strategy/simulator sources into a disposable private namespace,
without executing `smtm/__init__.py` or subpackage initializers. A minimal logging
adapter suppresses production log-file setup, and deterministic IDs replace only
`DateConverter.timestamp_id` in that private namespace. Production modules and
behavior in other processes are untouched.

Unknown relative source dependencies and unapproved absolute imports fail closed;
adding a new production dependency requires reviewing the allowlists. Tests cover
attempted config, dotenv, SDK and socket imports, including already-cached import
paths. The CLI installs a Python audit guard that rejects network/process attempts
and common `.env`, `.netrc`, `.aws`, `.ssh` file paths (after path resolution).
These are tested guardrails, **not an OS security sandbox** for malicious Python.
The fixture is JSON data only, never executable code or import-path configuration.
The importable `evaluate()` function does not install a process-global audit hook;
use the guarded CLI for standalone execution.

## Safe manual QA

Run the supplied fixture and check:

- BNH ends with equity approximately `1005.0435`, five fills and two rejected
  zero-size requests.
- Scripted LLM ends with cash `890`, quantity `1`, marked equity `990`, two fills
  and one end-of-run cancellation.
- LLM outcome counts include one hold, one rejected decision, one missing-data
  tick, one provider error and one missing tool. Fake calls total seven; known
  scripted usage totals 62 input / 17 output tokens, with one missing-usage call.
- Run again into a new file. Ignore runtime/timing fields and compare the other
  fields. Do not rank models or infer profitability from these hand-authored cases.

## Deterministic scenario regression suite

The fixture directory now contains five versioned synthetic cases:

- `synthetic-rising-v1`: 100 → 110 → 120 → 130.
- `synthetic-falling-v1`: 100 → 90 → 80 → 70.
- `synthetic-sideways-v1`: four quotes at 100.
- `synthetic-rejections-v1`: a missing first quote, boolean order size, unknown
  action, and sell without inventory. The real LLM strategy rejects all three
  decisions; no orders are emitted by that arm.
- `synthetic-smoke-v1`: the original mixed-price case, including a rejected
  decision, missing quote, fake provider error, missing decision tool, simulator
  zero-size rejections and terminal pending-order cancellation.

The three price-path cases use the same scripted buy of two units at 100 followed
by three holds. LLM final equity is respectively 1060, 940 and 1000; BNH final equity
is approximately 1113.028, 870.556 and 1000. These are arithmetic regression
expectations, **not performance rankings or market forecasts**. Both arms still
use the unchanged production strategies/simulator loaded by `evaluate_offline`.
Malformed *fixture structure* is rejected with exit 2; deliberately malformed
*decision values* are passed to the real strategy and captured as rejections.

Capture a baseline, then compare a second run (Python standard library only):

```sh
python -S tools/evaluate_regression.py \
  --fixtures tests/fixtures/evaluation --output /tmp/smtm-suite-before.json
python -S tools/evaluate_regression.py \
  --fixtures tests/fixtures/evaluation --baseline /tmp/smtm-suite-before.json \
  --output /tmp/smtm-suite-after.json
python -S -m unittest tests.unit_tests.offline_evaluation_test \
  tests.unit_tests.offline_regression_test -v
```

The directory is non-recursive and must contain only fixture `*.json` files.
Reports and baselines belong outside it. An empty/missing directory, invalid
fixture or duplicate scenario ID fails closed. Each run writes one **new** file;
it never overwrites a previous baseline or artifact. Capture without `--baseline`
is explicitly a capture, **not a passing regression comparison**. Keep a reviewed
baseline artifact when comparing a later code revision; do not silently regenerate
it after a failure. No automatic baseline approval or replacement is provided.

The suite artifact has `schema_version: 1`,
`evaluation_kind: "offline_scripted_suite"` and `reports` containing full original
reports, exact source and fixture hashes, runtime metadata and measured timings.
With `--baseline`, `comparison` additionally contains:

- `matches`: semantic equality across the same scenario IDs;
- `changed_paths`: scenario IDs mapped to differing JSON paths, or `added`/
  `removed` for scenario-set changes;
- `source_changed_scenarios`: source hash maps changed between the two artifacts.

Comparison ignores **only** per-report `runtime`, `fixture_file_sha256`,
`source_sha256`, `source_bundle_sha256`, and the tick/summary fields named
`local_decision_latency_ms`. Source changes remain visible separately: identical
outcomes after a source edit do not mean identical code or a complete safety
review. Fixture semantic hashes, config, limitations, decisions, prompt hashes,
requests, events, token accounting, equity, outcomes and unknown report fields
remain significant. Scenario order and JSON object key order do not matter;
ordered ticks/events and numeric types do. There is no floating-point tolerance,
so changes in Python arithmetic behavior can require explicit investigation.
The comparison metadata of a previous capture is not itself compared.

Exit codes: **0** means successful capture or a matching comparison (distinguish
using `comparison`); **1** means semantic changes, with a complete new report and
paths for investigation; **2** means invalid input or execution/file failure.
The same offline guard as the single-fixture CLI is installed. No trading,
provider calls, production runtime activation or deployment is added.
