"""Replay a local fixture suite and compare deterministic evaluation semantics.

No baseline is updated automatically. Exit 0 for a match (or a first capture),
1 for semantic changes, and 2 for invalid input or an execution/file error.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

try:
    from . import evaluate_offline as evaluation
except ImportError:  # Direct script execution, including python -S.
    import evaluate_offline as evaluation


def semantic_report(report):
    """Keep behavior and fixture identity; exclude explicit execution provenance.

    Source hashes are reported separately so a source edit is visible without
    making behavior-preserving refactors fail. Unknown fields remain significant.
    """
    if (
        not isinstance(report, dict)
        or type(report.get("schema_version")) is not int
        or report["schema_version"] != 1
        or report.get("evaluation_kind") != "offline_scripted_plumbing"
    ):
        raise ValueError("expected an offline_scripted_plumbing version 1 report")
    for field in ("scenario_id", "data_kind", "fixture_sha256"):
        if not isinstance(report.get(field), str) or not report[field]:
            raise ValueError("missing report identity: " + field)
    if not isinstance(report.get("config"), dict) or not report["config"]:
        raise ValueError("missing report config")
    result = copy.deepcopy(report)
    for field in (
        "runtime",
        "source_sha256",
        "source_bundle_sha256",
        "fixture_file_sha256",
    ):
        result.pop(field, None)
    arms = result.get("arms")
    if not isinstance(arms, list) or [a.get("strategy") for a in arms] != [
        "BNH",
        "LLM",
    ]:
        raise ValueError("expected ordered BNH and LLM arms")
    for arm in arms:
        summary = arm.get("summary")
        if not isinstance(summary, dict) or not {
            "final_account",
            "return_fraction",
            "max_sampled_drawdown_fraction",
            "outcome_counts",
            "filled_orders",
            "failed_orders",
            "canceled_orders",
            "fake_call_count",
            "scripted_token_totals",
            "usage_missing_call_count",
            "model_cost",
            "model_cost_status",
        }.issubset(summary):
            raise ValueError("incomplete arm summary")
        ticks = arm.get("ticks")
        if not isinstance(ticks, list) or not ticks:
            raise ValueError("arm ticks must be nonempty")
        for tick in ticks:
            if not isinstance(tick, dict) or not {
                "tick_index",
                "at",
                "snapshot_sha256",
                "outcome",
                "requests",
                "events",
                "account",
                "fake_calls",
                "scripted_usage",
            }.issubset(tick):
                raise ValueError("incomplete tick")
        if not isinstance(arm.get("finalization_events"), list):
            raise ValueError("missing finalization events")
        arm["summary"].pop("local_decision_latency_ms", None)
        for tick in arm["ticks"]:
            tick.pop("local_decision_latency_ms", None)
    evaluation.canonical_bytes(result)
    return result


def differences(before, after, path="$"):
    """Return deterministic JSON paths; do not apply numeric tolerances."""
    if type(before) is not type(after):
        return [path]
    if isinstance(before, dict):
        paths = []
        for key in sorted(set(before) | set(after)):
            child = path + "[" + json.dumps(key) + "]"
            paths.extend(
                [child]
                if key not in before or key not in after
                else differences(before[key], after[key], child)
            )
        return paths
    if isinstance(before, list):
        paths = []
        for index in range(max(len(before), len(after))):
            child = path + "[" + str(index) + "]"
            paths.extend(
                [child]
                if index >= len(before) or index >= len(after)
                else differences(before[index], after[index], child)
            )
        return paths
    return [] if before == after else [path]


def indexed_reports(suite):
    """Reject unsupported, empty or ambiguous baseline artifacts."""
    if (
        not isinstance(suite, dict)
        or type(suite.get("schema_version")) is not int
        or suite["schema_version"] != 1
        or suite.get("evaluation_kind") != "offline_scripted_suite"
    ):
        raise ValueError("expected offline_scripted_suite version 1")
    reports = suite.get("reports")
    if not isinstance(reports, list) or not reports:
        raise ValueError("suite reports must be nonempty")
    result = {}
    for report in reports:
        semantic_report(report)
        name = report.get("scenario_id")
        if not isinstance(name, str) or not name.strip() or name in result:
            raise ValueError("scenario_id must be nonempty and unique")
        result[name] = report
    return result


def compare_suites(baseline, candidate):
    """Compare by scenario ID, reporting added/removed scenarios as differences."""
    old, new = indexed_reports(baseline), indexed_reports(candidate)
    changes, source_changes = {}, []
    for name in sorted(set(old) | set(new)):
        if name not in old or name not in new:
            changes[name] = ["added" if name in new else "removed"]
            continue
        paths = differences(semantic_report(old[name]), semantic_report(new[name]))
        if paths:
            changes[name] = paths
        if old[name].get("source_sha256") != new[name].get("source_sha256"):
            source_changes.append(name)
    return {
        "matches": not changes,
        "changed_paths": changes,
        "source_changed_scenarios": source_changes,
    }


def run_suite(paths):
    """Use the unchanged evaluator for each fixture, preserving full reports."""
    reports = []
    for path in paths:
        raw = Path(path).read_bytes()
        report = evaluation.evaluate(json.loads(raw))
        report["fixture_file_sha256"] = hashlib.sha256(raw).hexdigest()
        reports.append(report)
    result = {
        "schema_version": 1,
        "evaluation_kind": "offline_scripted_suite",
        "reports": reports,
    }
    indexed_reports(result)
    return result


def main(argv=None):
    """Capture a new artifact and optionally compare a previous capture."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        required=True,
        help="Directory containing versioned fixture JSON files only",
    )
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    evaluation.install_offline_guard()
    try:
        if not args.fixtures.is_dir():
            raise ValueError("fixtures must be a directory")
        paths = sorted(args.fixtures.glob("*.json"))
        report = run_suite(paths)
        if args.baseline:
            baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
            report["comparison"] = compare_suites(baseline, report)
        with args.output.open("x", encoding="utf-8") as target:
            json.dump(report, target, ensure_ascii=False, indent=2, allow_nan=False)
            target.write("\n")
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OverflowError,
        OSError,
        RuntimeError,
        ImportError,
    ) as error:
        parser.exit(2, "Offline regression failed: " + str(error) + "\n")
    comparison = report.get("comparison")
    if comparison is not None and not comparison["matches"]:
        print(json.dumps(comparison, ensure_ascii=False, sort_keys=True))
        return 1
    print(
        "Offline suite "
        + ("matches baseline" if comparison else "captured (not a regression pass)")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
