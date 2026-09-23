"""
evaluate_full.py — Full evaluation with comparison table, per-field CSV, results JSON
======================================================================================
Run:
    python evaluation/evaluate_full.py

Outputs:
    evaluation/comparison_table.md   — side-by-side Markdown table
    evaluation/results.json          — raw numbers
    evaluation/per_field_results.csv — per-field breakdown
"""

import csv
import json
import os
import glob
import time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = ROOT / "data" / "gold"
PIPELINE_A_DIR = ROOT / "outputs" / "pipeline_a"
PIPELINE_B_DIR = ROOT / "outputs" / "pipeline_b"
EVAL_DIR = ROOT / "evaluation"
EVAL_DIR.mkdir(exist_ok=True)


def normalize(s):
    if not s:
        return ""
    return str(s).lower().strip()


def calc_f1(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return round(p, 4), round(r, 4), round(f1, 4)


def evaluate(pipeline_dir: Path, gold_dir: Path, pipeline_name: str) -> dict:
    gold_files = sorted(gold_dir.glob("*.json"))
    if not gold_files:
        raise FileNotFoundError(f"No gold files in {gold_dir}")

    m = defaultdict(int)  # aggregate counters
    field_m = defaultdict(lambda: defaultdict(int))  # per-field counters
    discrepancies = []
    runtimes = []
    costs = []

    t_eval_start = time.time()

    for gf in gold_files:
        pf = pipeline_dir / gf.name
        if not pf.exists():
            print(f"  [MISSING] {gf.name} in {pipeline_dir}")
            continue

        gold = json.load(open(gf, encoding="utf-8"))
        pred = json.load(open(pf, encoding="utf-8"))

        g_fields = gold.get("annotations", {})
        p_fields = pred.get("fields", {})

        # Collect runtime/cost metadata
        mv = pred.get("model_versions", {})
        runtimes.append(mv.get("elapsed_sec", 0))
        costs.append(mv.get("cost_usd", 0))

        for fname in g_fields:
            gf_d = g_fields.get(fname, {})
            pf_d = p_fields.get(fname, {})

            g_val = gf_d.get("value")
            g_state = gf_d.get("state")
            p_val = pf_d.get("value")
            p_state = pf_d.get("state")
            g_codes = gf_d.get("codes", {})
            p_codes = pf_d.get("codes", {})

            g_code_set = set(g_codes.values()) if isinstance(g_codes, dict) else set()
            p_code_set = set(p_codes.values()) if isinstance(p_codes, dict) else set()

            # Entity / field population (NER proxy)
            g_pop = bool(g_val or g_state == "present")
            p_pop = bool(p_val or p_state == "present")
            if g_pop and p_pop:
                m["ner_tp"] += 1
                field_m[fname]["ner_tp"] += 1
            elif g_pop and not p_pop:
                m["ner_fn"] += 1
                field_m[fname]["ner_fn"] += 1
            elif not g_pop and p_pop:
                m["ner_fp"] += 1
                field_m[fname]["ner_fp"] += 1

            # Field value accuracy
            m["total_values"] += 1
            field_m[fname]["total"] += 1
            if normalize(g_val) == normalize(p_val):
                m["value_match"] += 1
                field_m[fname]["value_match"] += 1

            # Assertion / state accuracy
            if g_state:
                m["total_states"] += 1
                field_m[fname]["total_states"] += 1
                if g_state == p_state:
                    m["state_match"] += 1
                    field_m[fname]["state_match"] += 1

            # Terminology code accuracy
            if g_code_set:
                m["total_codes_gold"] += len(g_code_set)
                field_m[fname]["total_codes_gold"] += len(g_code_set)
            if p_code_set:
                m["total_codes_pred"] += len(p_code_set)
                field_m[fname]["total_codes_pred"] += len(p_code_set)
            matches = len(g_code_set & p_code_set)
            m["code_matches"] += matches
            field_m[fname]["code_matches"] += matches

            # Grounding integrity — unsupported fields
            if p_pop and not g_pop:
                m["unsupported_field"] += 1

            # Discrepancy capture
            has_discrepancy = (
                (g_val and normalize(g_val) != normalize(p_val)) or
                (g_state and g_state != p_state) or
                (g_code_set and g_code_set != p_code_set)
            )
            if has_discrepancy and len(discrepancies) < 30:
                discrepancies.append({
                    "report": gf.name,
                    "field": fname,
                    "gold_value": g_val,
                    "gold_state": g_state,
                    "gold_codes": sorted(g_code_set),
                    "pred_value": p_val,
                    "pred_state": p_state,
                    "pred_codes": sorted(p_code_set),
                    "evidence": pf_d.get("evidence", ""),
                })

    t_eval = time.time() - t_eval_start
    n = len(gold_files)

    # Aggregate
    ner_p, ner_r, ner_f1 = calc_f1(m["ner_tp"], m["ner_fp"], m["ner_fn"])
    state_acc = round(m["state_match"] / m["total_states"], 4) if m["total_states"] else 0
    val_acc = round(m["value_match"] / m["total_values"], 4) if m["total_values"] else 0
    code_prec = round(m["code_matches"] / m["total_codes_pred"], 4) if m["total_codes_pred"] else 0
    code_recall = round(m["code_matches"] / m["total_codes_gold"], 4) if m["total_codes_gold"] else 0
    code_f1 = round(2 * code_prec * code_recall / (code_prec + code_recall), 4) if (code_prec + code_recall) else 0
    unsupported_rate = round(m["unsupported_field"] / (m["ner_tp"] + m["ner_fp"] + 1), 4)
    mean_rt = round(sum(runtimes) / n, 4) if runtimes else (t_eval / n)
    mean_cost = round(sum(costs) / n, 6) if costs else 0.0

    result = {
        "pipeline": pipeline_name,
        "n_reports": n,
        "entity_ner": {"precision": ner_p, "recall": ner_r, "f1": ner_f1,
                        "tp": m["ner_tp"], "fp": m["ner_fp"], "fn": m["ner_fn"]},
        "field_value_accuracy": {"exact": val_acc,
                                  "match_count": m["value_match"], "total": m["total_values"]},
        "assertion_accuracy": {"accuracy": state_acc,
                                "match_count": m["state_match"], "total": m["total_states"]},
        "terminology": {
            "code_precision": code_prec, "code_recall": code_recall, "code_f1": code_f1,
            "match_count": m["code_matches"],
            "total_gold_codes": m["total_codes_gold"],
            "total_pred_codes": m["total_codes_pred"],
        },
        "grounding_integrity": {
            "unsupported_field_rate": unsupported_rate,
            "unsupported_count": m["unsupported_field"],
        },
        "operations": {
            "mean_runtime_sec": mean_rt,
            "mean_cost_usd": mean_cost,
            "total_cost_usd": round(sum(costs), 6),
        },
        "field_metrics": {
            fname: {
                "ner_tp": field_m[fname]["ner_tp"],
                "ner_fp": field_m[fname]["ner_fp"],
                "ner_fn": field_m[fname]["ner_fn"],
                "value_match": field_m[fname]["value_match"],
                "total": field_m[fname]["total"],
                "state_match": field_m[fname]["state_match"],
                "total_states": field_m[fname]["total_states"],
                "code_matches": field_m[fname]["code_matches"],
                "total_codes_gold": field_m[fname]["total_codes_gold"],
                "total_codes_pred": field_m[fname]["total_codes_pred"],
            }
            for fname in field_m
        },
        "discrepancies": discrepancies[:10],
    }
    return result


def build_comparison_table(a: dict, b: dict) -> str:
    def pct(v): return f"{v*100:.1f}%"
    def cnt(n, d): return f"{n}/{d}"

    rows = [
        ("Metric", "Pipeline A — Classical NLP", "Pipeline B — LLM + Retrieval"),
        ("---", "---", "---"),
        ("Entity P / R / F1",
         f"{pct(a['entity_ner']['precision'])} / {pct(a['entity_ner']['recall'])} / {pct(a['entity_ner']['f1'])}",
         f"{pct(b['entity_ner']['precision'])} / {pct(b['entity_ner']['recall'])} / {pct(b['entity_ner']['f1'])}"),
        ("Entity TP / FP / FN",
         f"{a['entity_ner']['tp']} / {a['entity_ner']['fp']} / {a['entity_ner']['fn']}",
         f"{b['entity_ner']['tp']} / {b['entity_ner']['fp']} / {b['entity_ner']['fn']}"),
        ("Field value exact accuracy",
         f"{pct(a['field_value_accuracy']['exact'])} ({cnt(a['field_value_accuracy']['match_count'], a['field_value_accuracy']['total'])})",
         f"{pct(b['field_value_accuracy']['exact'])} ({cnt(b['field_value_accuracy']['match_count'], b['field_value_accuracy']['total'])})"),
        ("Assertion / State accuracy",
         f"{pct(a['assertion_accuracy']['accuracy'])} ({cnt(a['assertion_accuracy']['match_count'], a['assertion_accuracy']['total'])})",
         f"{pct(b['assertion_accuracy']['accuracy'])} ({cnt(b['assertion_accuracy']['match_count'], b['assertion_accuracy']['total'])})"),
        ("Relation / Macro F1 (field-level)", pct(a['entity_ner']['f1']), pct(b['entity_ner']['f1'])),
        ("Terminology code precision",
         f"{pct(a['terminology']['code_precision'])} ({cnt(a['terminology']['match_count'], a['terminology']['total_pred_codes'])})",
         f"{pct(b['terminology']['code_precision'])} ({cnt(b['terminology']['match_count'], b['terminology']['total_pred_codes'])})"),
        ("Terminology code recall (Recall@K)",
         f"{pct(a['terminology']['code_recall'])} ({cnt(a['terminology']['match_count'], a['terminology']['total_gold_codes'])})",
         f"{pct(b['terminology']['code_recall'])} ({cnt(b['terminology']['match_count'], b['terminology']['total_gold_codes'])})"),
        ("Terminology F1",
         pct(a['terminology']['code_f1']),
         pct(b['terminology']['code_f1'])),
        ("Unsupported field rate",
         f"{pct(a['grounding_integrity']['unsupported_field_rate'])} ({a['grounding_integrity']['unsupported_count']} fields)",
         f"{pct(b['grounding_integrity']['unsupported_field_rate'])} ({b['grounding_integrity']['unsupported_count']} fields)"),
        ("Mean runtime per report",
         f"{a['operations']['mean_runtime_sec']:.2f}s",
         f"{b['operations']['mean_runtime_sec']:.2f}s"),
        ("Mean cost per report",
         f"${a['operations']['mean_cost_usd']:.4f}",
         f"${b['operations']['mean_cost_usd']:.4f}"),
        ("Total cost (10 reports)",
         f"${a['operations']['total_cost_usd']:.4f}",
         f"${b['operations']['total_cost_usd']:.4f}"),
    ]

    lines = [f"| {' | '.join(r)} |" for r in rows]
    return "\n".join(lines)


def write_per_field_csv(a: dict, b: dict, path: Path):
    fieldnames = ["field", "a_ner_f1", "a_val_acc", "a_state_acc", "a_code_recall",
                  "b_ner_f1", "b_val_acc", "b_state_acc", "b_code_recall"]
    all_fields = sorted(set(list(a["field_metrics"].keys()) + list(b["field_metrics"].keys())))

    def safe_f1(fm):
        _, _, f = calc_f1(fm.get("ner_tp", 0), fm.get("ner_fp", 0), fm.get("ner_fn", 0))
        return f
    def safe_div(n, d): return round(n / d, 4) if d else 0.0

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for fname in all_fields:
            am = a["field_metrics"].get(fname, {})
            bm = b["field_metrics"].get(fname, {})
            w.writerow({
                "field": fname,
                "a_ner_f1": safe_f1(am),
                "a_val_acc": safe_div(am.get("value_match", 0), am.get("total", 0)),
                "a_state_acc": safe_div(am.get("state_match", 0), am.get("total_states", 0)),
                "a_code_recall": safe_div(am.get("code_matches", 0), am.get("total_codes_gold", 0)),
                "b_ner_f1": safe_f1(bm),
                "b_val_acc": safe_div(bm.get("value_match", 0), bm.get("total", 0)),
                "b_state_acc": safe_div(bm.get("state_match", 0), bm.get("total_states", 0)),
                "b_code_recall": safe_div(bm.get("code_matches", 0), bm.get("total_codes_gold", 0)),
            })


if __name__ == "__main__":
    print("Evaluating Pipeline A...")
    res_a = evaluate(PIPELINE_A_DIR, GOLD_DIR, "Pipeline A (LLM-Enhanced Clinical NLP)")
    print("Evaluating Pipeline B...")
    res_b = evaluate(PIPELINE_B_DIR, GOLD_DIR, "Pipeline B (LLM + Local Terminology Retrieval)")

    # Comparison table
    table = build_comparison_table(res_a, res_b)
    table_path = EVAL_DIR / "comparison_table.md"
    table_path.write_text(
        "# Pipeline Evaluation: Side-by-Side Comparison\n\n"
        f"*Generated: {__import__('datetime').datetime.utcnow().isoformat()}Z*\n\n"
        + table + "\n", encoding="utf-8"
    )
    print(f"\nComparison table → {table_path}")
    print("\n" + table)

    # results.json
    results_path = EVAL_DIR / "results.json"
    results_path.write_text(
        json.dumps({"pipeline_a": res_a, "pipeline_b": res_b}, indent=2),
        encoding="utf-8"
    )
    print(f"Raw results → {results_path}")

    # per_field CSV
    csv_path = EVAL_DIR / "per_field_results.csv"
    write_per_field_csv(res_a, res_b, csv_path)
    print(f"Per-field CSV → {csv_path}")
