# Offline context snapshot tests

`tests/unit_tests/offline_context_snapshot_test.py` characterizes the current
context consumers using synthetic values and scripted LLM responses. The suite
starts no trading session, creates no trader, and calls no external API.

## Test helpers

`tests.e2e_tests.fake_llm_client.FakeSnapshotDataProvider` accepts a **list of
snapshots**, where each snapshot is the complete list returned by one
`get_info()` call. Mixed typed items retain their order:

```python
provider = FakeSnapshotDataProvider([
    [synthetic_candle, synthetic_news, synthetic_funding],
    [],
    [next_synthetic_candle],
])
```

The three calls return those three complete snapshots. Later calls repeat the
last snapshot. An empty timeline (`[]`) always returns `[]`; an explicitly empty
snapshot (`[[]]`) also remains empty. No default candle is inserted. The input
must be a list of lists of dictionaries; a flat mixed list raises `TypeError`
instead of silently becoming a sequence of single-item ticks. This validates the
fixture's container shape, not production data schemas or freshness.

Construction copies the complete timeline, and each read returns a deep copy.
Changing the original fixture or a returned nested value therefore cannot
rewrite another read. `call_count` increments once per read, including empty
and exhausted timelines.

The existing `FakeDataProvider(candles=...)` is unchanged: multiple candles are
successive single-candle reads, exhaustion repeats the last candle, and its
legacy empty constructor input selects a default candle. Use the explicit new
helper for empty or mixed snapshots. `FakeLlmClient.call_log` now deep-copies
request arguments at each call so later tool-loop appends or nested mutations
cannot rewrite an earlier captured request. Its scripted response behavior is
unchanged.

## Current route boundary

- The real `MarketDataTool` and `ToolRouter` return the complete mixed provider
  snapshot. The chat test inspects the subsequent `SystemOperator` LLM request's
  `tool_result`, including order, values, and an empty response.
- The real `StrategyLlm` currently stores only the first `primary_candle` from a
  snapshot. The hold test verifies that candle in its prompt, excludes the
  non-candle fixture markers, makes one forced `submit_decision` call, and emits
  no order. A fresh strategy receiving only empty/non-candle data makes no call.
- An empty snapshot does not clear a previously populated strategy history.
  The tests record this existing behavior; they do not add freshness or stale
  candle protection.

These are baseline characterizations, not a decision that future strategies
must remain candle-only. News/funding/sentiment propagation, strategy-knowledge
wiring, context limits, and tool-loop budgets need separately scoped runtime
changes. This test-only slice does not validate trading performance or improve
the data delivered to a live trading prompt.

## Verification

In a disposable environment with no credentials, dotenv loading disabled, and
outbound network access denied, run:

```bash
python -m pytest tests/unit_tests/offline_context_snapshot_test.py -q
python -m pytest tests/e2e_tests/ -q
python -m pytest tests/unit_tests/ -q
```

The new regression file lives in the existing unit-test CI discovery path;
the existing CI workflow is unchanged. The E2E command remains a separate
verification step. Existing E2E scenarios use virtual `SimulationTrader`
orders; the new context suite uses only a read-only market tool and standalone
hold decisions, without a trader or timer.

The fixtures are hand-authored synthetic records, not downloaded news, recorded
account data, or a live provider capture. Normal exact-head CI and any local
dependency limitations should be recorded separately in the PR.
