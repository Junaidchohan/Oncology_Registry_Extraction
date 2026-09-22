"""
validate.py
===========
Validates pipeline outputs (Pipeline A and Pipeline B) against the shared JSON schema
and optionally computes field-level agreement against gold annotations.

Usage:
    python src/common/validate.py --pipeline-a outputs/pipeline_a/ --pipeline-b outputs/pipeline_b/ --gold data/gold/
    python src/common/validate.py --pipeline-a outputs/pipeline_a/  # validate one pipeline only
    python src/common/validate.py --file outputs/pipeline_a/report_001.json  # validate single file
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Allow running as a script from the project root
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from schema import (  # noqa: E402
    FIELD_NAMES,
    OUTPUT_JSON_SCHEMA,
    VALID_PIPELINES,
    VALID_STATES,
)

# Optional jsonschema import
try:
    import jsonschema
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when a pipeline output file fails schema validation."""


def _manual_validate(data: Dict[str, Any], filepath: str) -> List[str]:
    """
    Perform manual (no jsonschema dependency) schema validation.
    Returns a list of error strings (empty = valid).
    """
    errors: List[str] = []

    # Top-level keys
    for req in ["report_id", "pipeline", "run_timestamp", "model_versions", "fields"]:
        if req not in data:
            errors.append(f"Missing required top-level key: '{req}'")

    if "pipeline" in data and data["pipeline"] not in VALID_PIPELINES:
        errors.append(f"Invalid pipeline '{data['pipeline']}'. Must be one of {sorted(VALID_PIPELINES)}")

    if "fields" not in data:
        return errors  # can't check further

    fields = data["fields"]
    if not isinstance(fields, dict):
        errors.append("'fields' must be a JSON object")
        return errors

    # Check all 21 fields are present
    for fname in FIELD_NAMES:
        if fname not in fields:
            errors.append(f"Missing field: '{fname}'")
            continue

        field = fields[fname]
        if not isinstance(field, dict):
            errors.append(f"Field '{fname}' must be an object, got {type(field).__name__}")
            continue

        for req_key in ["value", "unit", "state", "evidence", "span", "codes"]:
            if req_key not in field:
                errors.append(f"Field '{fname}' missing key '{req_key}'")

        if "state" in field:
            if field["state"] not in VALID_STATES:
                errors.append(
                    f"Field '{fname}' has invalid state '{field['state']}'. "
                    f"Must be one of {sorted(VALID_STATES)}"
                )

        if "span" in field and field["span"] is not None:
            span = field["span"]
            if not (isinstance(span, list) and len(span) == 2 and all(isinstance(i, int) for i in span)):
                errors.append(f"Field '{fname}'.span must be null or [int, int], got {span!r}")

        if "codes" in field and not isinstance(field.get("codes"), dict):
            errors.append(f"Field '{fname}'.codes must be an object")

    return errors


def validate_file(filepath: str) -> Tuple[bool, List[str]]:
    """
    Validate a single pipeline output JSON file.
    Returns (is_valid, list_of_errors).
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"JSON parse error: {e}"]
    except FileNotFoundError:
        return False, [f"File not found: {filepath}"]

    if _HAS_JSONSCHEMA:
        validator = jsonschema.Draft7Validator(OUTPUT_JSON_SCHEMA)
        errors = [str(e.message) for e in validator.iter_errors(data)]
    else:
        errors = _manual_validate(data, filepath)

    return len(errors) == 0, errors


def validate_directory(directory: str) -> Dict[str, Tuple[bool, List[str]]]:
    """Validate all JSON files in a directory. Returns {filename: (valid, errors)}."""
    results: Dict[str, Tuple[bool, List[str]]] = {}
    dirpath = Path(directory)
    if not dirpath.exists():
        print(f"  [WARN] Directory does not exist: {directory}")
        return results

    json_files = sorted(dirpath.glob("report_*.json"))
    if not json_files:
        print(f"  [WARN] No report_*.json files found in: {directory}")
        return results

    for fpath in json_files:
        valid, errs = validate_file(str(fpath))
        results[fpath.name] = (valid, errs)

    return results


# ---------------------------------------------------------------------------
# Agreement scoring (against gold)
# ---------------------------------------------------------------------------

def compute_agreement(
    pred_path: str,
    gold_path: str,
) -> Dict[str, Any]:
    """
    Compare a pipeline output JSON to a gold annotation JSON.
    Returns per-field agreement metrics.
    """
    try:
        with open(pred_path, encoding="utf-8") as f:
            pred = json.load(f)
        with open(gold_path, encoding="utf-8") as f:
            gold = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"error": str(e)}

    pred_fields = pred.get("fields", {})
    gold_fields = gold.get("annotations", {})  # gold uses "annotations" key

    results: Dict[str, Any] = {}
    state_matches = 0
    value_matches = 0
    total = 0

    for fname in FIELD_NAMES:
        pred_f = pred_fields.get(fname, {})
        gold_f = gold_fields.get(fname, {})

        pred_state = pred_f.get("state", "not_mentioned")
        gold_state = gold_f.get("state", "not_mentioned")

        # Normalise gold state (gold uses "not_mentioned" with underscore)
        gold_state = gold_state.replace(" ", "_")

        state_match = pred_state == gold_state
        # Loose value match: both are non-null and have overlapping text
        pred_val = (pred_f.get("value") or "").lower()
        gold_val = (gold_f.get("value") or "").lower()
        value_match = bool(pred_val and gold_val and (
            pred_val in gold_val or gold_val in pred_val
        ))

        results[fname] = {
            "pred_state": pred_state,
            "gold_state": gold_state,
            "state_match": state_match,
            "pred_value": pred_f.get("value"),
            "gold_value": gold_f.get("value"),
            "value_match": value_match,
        }

        state_matches += int(state_match)
        value_matches += int(value_match)
        total += 1

    results["_summary"] = {
        "total_fields": total,
        "state_exact_matches": state_matches,
        "state_accuracy": round(state_matches / total, 4) if total else 0.0,
        "value_partial_matches": value_matches,
        "value_partial_accuracy": round(value_matches / total, 4) if total else 0.0,
    }
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _print_results(label: str, results: Dict[str, Tuple[bool, List[str]]]) -> int:
    """Print validation results. Returns total error count."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    total_errors = 0
    if not results:
        print("  No files validated.")
        return 0
    for fname, (valid, errs) in sorted(results.items()):
        status = "PASS" if valid else "FAIL"
        print(f"  [{status}] {fname}")
        for e in errs:
            print(f"         ERROR: {e}")
            total_errors += 1
    print(f"\n  Total: {len(results)} files | {sum(v for v, _ in results.values())} passed | "
          f"{sum(not v for v, _ in results.values())} failed")
    return total_errors


def _print_agreement(
    pipeline_dir: str,
    gold_dir: str,
    pipeline_label: str,
) -> None:
    """Print field-level agreement between pipeline output and gold."""
    pred_path = Path(pipeline_dir)
    gold_path = Path(gold_dir)
    if not pred_path.exists() or not gold_path.exists():
        return

    print(f"\n{'='*60}")
    print(f"  Agreement: {pipeline_label} vs Gold")
    print(f"{'='*60}")

    all_state_acc: List[float] = []
    for gf in sorted(gold_path.glob("report_*.json")):
        pf = pred_path / gf.name
        if not pf.exists():
            print(f"  [SKIP] {gf.name} — prediction not found")
            continue
        agreement = compute_agreement(str(pf), str(gf))
        if "error" in agreement:
            print(f"  [ERR]  {gf.name}: {agreement['error']}")
            continue
        summary = agreement.get("_summary", {})
        acc = summary.get("state_accuracy", 0.0)
        all_state_acc.append(acc)
        print(f"  {gf.name}: state_accuracy={acc:.1%}  value_partial={summary.get('value_partial_accuracy', 0):.1%}")

    if all_state_acc:
        avg = sum(all_state_acc) / len(all_state_acc)
        print(f"\n  Mean state accuracy across {len(all_state_acc)} reports: {avg:.1%}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate pipeline output JSON files against the shared schema."
    )
    parser.add_argument("--file", help="Validate a single JSON file")
    parser.add_argument("--pipeline-a", help="Directory containing Pipeline A outputs")
    parser.add_argument("--pipeline-b", help="Directory containing Pipeline B outputs")
    parser.add_argument("--gold", help="Directory containing gold annotations (for agreement scoring)")
    args = parser.parse_args()

    if not any([args.file, args.pipeline_a, args.pipeline_b]):
        parser.print_help()
        sys.exit(1)

    if not _HAS_JSONSCHEMA:
        print("[WARN] jsonschema not installed — using built-in manual validation.")
        print("       Install with: pip install jsonschema\n")

    total_errors = 0

    if args.file:
        valid, errs = validate_file(args.file)
        status = "PASS" if valid else "FAIL"
        print(f"[{status}] {args.file}")
        for e in errs:
            print(f"  ERROR: {e}")
        total_errors += len(errs)

    if args.pipeline_a:
        results_a = validate_directory(args.pipeline_a)
        total_errors += _print_results("Pipeline A — Classical NLP", results_a)
        if args.gold:
            _print_agreement(args.pipeline_a, args.gold, "Pipeline A")

    if args.pipeline_b:
        results_b = validate_directory(args.pipeline_b)
        total_errors += _print_results("Pipeline B — LLM + Retrieval", results_b)
        if args.gold:
            _print_agreement(args.pipeline_b, args.gold, "Pipeline B")

    print(f"\n{'='*60}")
    if total_errors == 0:
        print("  ALL VALIDATIONS PASSED")
    else:
        print(f"  VALIDATION FAILED — {total_errors} total error(s)")
    print(f"{'='*60}\n")

    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
