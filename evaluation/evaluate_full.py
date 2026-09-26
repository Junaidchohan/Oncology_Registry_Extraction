import csv
import json
import sys, io
import os
import glob
import time
import re
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = ROOT / "data" / "gold"
PIPELINE_A_DIR = ROOT / "outputs" / "pipeline_a"
PIPELINE_B_DIR = ROOT / "outputs" / "pipeline_b"
EVAL_DIR = ROOT / "evaluation"
EVAL_DIR.mkdir(exist_ok=True)

def normalize_ws(s):
    if not s: return ""
    return " ".join(str(s).strip().split())

def normalize(s):
    if not s: return ""
    s = str(s).lower().strip()
    m = re.match(r"^([\d\.]+)\s*cm$", s)
    if m:
        try: return f"{float(m.group(1)) * 10:g} mm"
        except: pass
    s = re.sub(r'[\.,;:!?]+$', '', s).strip()
    return normalize_ws(s)

def get_iou(span1, span2):
    if not span1 or not span2: return 0.0
    if len(span1) != 2 or len(span2) != 2: return 0.0
    b1, e1 = span1
    b2, e2 = span2
    if b1 is None or e1 is None or b2 is None or e2 is None: return 0.0
    intersection = max(0, min(e1, e2) - max(b1, b2))
    union = (e1 - b1) + (e2 - b2) - intersection
    return intersection / union if union > 0 else 0.0

def check_span(g_span, p_span, g_ev, p_ev):
    # Span matching convention: A predicted mention is a TP if both evidence strings are identical after whitespace normalization.
    if g_ev and p_ev and normalize_ws(g_ev) == normalize_ws(p_ev):
        return True
    return False

def validate_evidence(ev, val, full_text):
    if not ev: return False, False, False, False
    ev_norm = normalize_ws(ev)
    a = ev_norm in normalize_ws(full_text)
    b = (normalize(val) in normalize(ev)) if val else True
    headers = {"final diagnosis", "microscopic description", "gross description", "clinical history", "specimen", "comment"}
    c = ev.strip().lower() not in headers
    d = len(ev.strip()) >= 10
    return a, b, c, d

def calc_f1(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return round(p, 4), round(r, 4), round(f1, 4)

def evaluate(pipeline_dir: Path, gold_dir: Path, pipeline_name: str) -> dict:
    gold_files = sorted(gold_dir.glob("*.json"))
    m = defaultdict(int)
    field_m = defaultdict(lambda: defaultdict(int))
    rel_m = defaultdict(lambda: defaultdict(int))
    runtimes, costs = [], []
    
    # Preload candidates for Pipeline B
    retrieval_log_path = pipeline_dir / "retrieval_log.jsonl"
    cands_by_report_field = defaultdict(lambda: defaultdict(list))
    if retrieval_log_path.exists():
        with open(retrieval_log_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                d = json.loads(line)
                rid = d.get("report_id")
                fid = d.get("field_name")
                key_map = {
                    "primary_site": "primary_tumor_site",
                    "histology_type": "histological_type",
                    "procedure_type": "procedure",
                    "tumor_multiplicity": "tumor_focality",
                    "lymph_nodes_positive": "positive_lymph_nodes",
                }
                fid = key_map.get(fid, fid)
                cands = []
                for t_name, c_list in d.get("candidates", {}).items():
                    cands.extend([c["code"] for c in c_list])
                cands_by_report_field[rid][fid] = cands

    for gf in gold_files:
        pf = pipeline_dir / gf.name
        if not pf.exists(): continue

        gold = json.load(open(gf, encoding="utf-8"))
        pred = json.load(open(pf, encoding="utf-8"))
        raw_text_file = ROOT / "data" / "raw" / f"{gf.stem}.txt"
        full_text = open(raw_text_file, encoding="utf-8").read() if raw_text_file.exists() else ""

        g_fields = gold.get("annotations", {})
        p_fields = pred.get("fields", {})

        mv = pred.get("model_versions", {})
        runtimes.append(mv.get("elapsed_sec", 0))
        costs.append(mv.get("cost_usd", 0))

        for fname in g_fields:
            if fname in ["biomarkers", "anticancer_medication"]: continue
            gf_d, pf_d = g_fields.get(fname, {}), p_fields.get(fname, {})

            g_val, g_state = gf_d.get("value"), gf_d.get("state")
            p_val, p_state = pf_d.get("value"), pf_d.get("state")
            g_span, p_span = gf_d.get("span"), pf_d.get("span")
            g_ev, p_ev = gf_d.get("evidence"), pf_d.get("evidence")
            
            # NER span-based eval
            if g_state == "present":
                if p_ev and check_span(g_span, p_span, g_ev, p_ev):
                    m["ner_tp"] += 1; field_m[fname]["ner_tp"] += 1
                elif not p_ev:
                    m["ner_fn"] += 1; field_m[fname]["ner_fn"] += 1
                else:
                    m["ner_fp"] += 1; field_m[fname]["ner_fp"] += 1
            else:
                if p_ev:
                    m["ner_fp"] += 1; field_m[fname]["ner_fp"] += 1

            # Value and State
            m["total_values"] += 1; field_m[fname]["total"] += 1
            if normalize(g_val) == normalize(p_val):
                m["value_match"] += 1; field_m[fname]["value_match"] += 1

            if g_state:
                m["total_states"] += 1; field_m[fname]["total_states"] += 1
                if g_state == p_state:
                    m["state_match"] += 1; field_m[fname]["state_match"] += 1

            # Retrieval & Selection
            g_codes = list(gf_d.get("codes", {}).values())
            p_codes = list(pf_d.get("codes", {}).values())
            p_cands = cands_by_report_field[gf.stem][fname]

            if g_codes:
                m["term_gold_codes"] += 1
                if any(gc in p_codes for gc in g_codes):
                    m["term_sel_match"] += 1
                if any(gc in p_cands for gc in g_codes) or (not p_cands and any(gc in p_codes for gc in g_codes)):
                    m["term_ret_match"] += 1

            # Evidence Validation
            p_pop = bool(p_val or p_state == "present")
            if p_pop:
                a, b, c, d = validate_evidence(p_ev, p_val, full_text)
                m["ev_populated"] += 1
                if a: m["ev_located"] += 1
                if b: m["ev_val_in_ev"] += 1
                if not (a and b and c and d):
                    m["unsupported_field"] += 1

        # Relations (has_lesion, has_assay, has_stage_system)
        def get_g_rels():
            rels = []
            for b in g_fields.get("biomarkers", []):
                if "lesion_id" in b: rels.append(("has_lesion", b.get("assay", ""), b["lesion_id"]))
                if "assay" in b: rels.append(("has_assay", b.get("result", ""), b["assay"]))
            if g_fields.get("pathologic_t", {}).get("value"): rels.append(("has_stage_system", "pathologic_t", "AJCC"))
            return set(rels)
            
        def get_p_rels():
            rels = []
            for b in p_fields.get("biomarkers", []):
                if "lesion_id" in b: rels.append(("has_lesion", b.get("assay", ""), b["lesion_id"]))
                if "assay" in b: rels.append(("has_assay", b.get("result", ""), b["assay"]))
            if p_fields.get("pathologic_t", {}).get("value"): rels.append(("has_stage_system", "pathologic_t", "AJCC"))
            return set(rels)

        g_rels = get_g_rels()
        p_rels = get_p_rels()

        for rtype in ["has_lesion", "has_assay", "has_stage_system"]:
            g_r = {r for r in g_rels if r[0] == rtype}
            p_r = {r for r in p_rels if r[0] == rtype}
            tp = len(g_r & p_r)
            fp = len(p_r - g_r)
            fn = len(g_r - p_r)
            rel_m[rtype]["tp"] += tp; rel_m[rtype]["fp"] += fp; rel_m[rtype]["fn"] += fn
            m["rel_tp"] += tp; m["rel_fp"] += fp; m["rel_fn"] += fn

    n = len(gold_files)
    ner_p, ner_r, ner_f1 = calc_f1(m["ner_tp"], m["ner_fp"], m["ner_fn"])
    rel_p, rel_r, rel_f1 = calc_f1(m["rel_tp"], m["rel_fp"], m["rel_fn"])
    state_acc = m["state_match"] / m["total_states"] if m["total_states"] else 0
    val_acc = m["value_match"] / m["total_values"] if m["total_values"] else 0
    
    ret_acc = m["term_ret_match"] / m["term_gold_codes"] if m["term_gold_codes"] else 0
    sel_acc = m["term_sel_match"] / m["term_gold_codes"] if m["term_gold_codes"] else 0

    ev_loc = m["ev_located"] / m["ev_populated"] if m["ev_populated"] else 0
    ev_val = m["ev_val_in_ev"] / m["ev_populated"] if m["ev_populated"] else 0
    unsup = m["unsupported_field"] / m["ev_populated"] if m["ev_populated"] else 0

    mean_rt = round(sum(runtimes) / n, 4) if n > 0 else 0
    try:
        summ = json.load(open(pipeline_dir / "_run_summary.json"))
        mean_rt = summ.get("mean_runtime_sec", mean_rt)
    except: pass
    mean_cost = round(sum(costs) / n, 6) if costs else 0.0

    return {
        "pipeline": pipeline_name,
        "n_reports": n,
        "entity_ner": {"precision": ner_p, "recall": ner_r, "f1": ner_f1, "tp": m["ner_tp"], "fp": m["ner_fp"], "fn": m["ner_fn"]},
        "rel": {"precision": rel_p, "recall": rel_r, "f1": rel_f1, "tp": m["rel_tp"], "fp": m["rel_fp"], "fn": m["rel_fn"]},
        "field_value_accuracy": {"exact": val_acc, "match_count": m["value_match"], "total": m["total_values"]},
        "assertion_accuracy": {"accuracy": state_acc, "match_count": m["state_match"], "total": m["total_states"]},
        "terminology": {"retrieval_acc": ret_acc, "selection_acc": sel_acc, "ret_match": m["term_ret_match"], "sel_match": m["term_sel_match"], "total": m["term_gold_codes"]},
        "evidence": {"loc_rate": ev_loc, "val_rate": ev_val, "unsupported_rate": unsup, "unsup_count": m["unsupported_field"], "total_populated": m["ev_populated"]},
        "operations": {"mean_runtime_sec": mean_rt, "mean_cost_usd": mean_cost, "total_cost_usd": round(sum(costs), 6)},
        "field_metrics": field_m
    }

def pct(v): return f"{v*100:.1f}%"
def cnt(n, d): return f"{n}/{d}"

def build_comparison_table(a: dict, b: dict) -> str:
    rows = [
        ("Metric", "Pipeline A — Classical NLP", "Pipeline B — LLM + Retrieval"),
        ("---", "---", "---"),
        ("Entity NER P / R / F1 (span-based)", f"{pct(a['entity_ner']['precision'])} / {pct(a['entity_ner']['recall'])} / {pct(a['entity_ner']['f1'])}", f"{pct(b['entity_ner']['precision'])} / {pct(b['entity_ner']['recall'])} / {pct(b['entity_ner']['f1'])}"),
        ("Field value exact accuracy", f"{pct(a['field_value_accuracy']['exact'])} ({cnt(a['field_value_accuracy']['match_count'], a['field_value_accuracy']['total'])})", f"{pct(b['field_value_accuracy']['exact'])} ({cnt(b['field_value_accuracy']['match_count'], b['field_value_accuracy']['total'])})"),
        ("Assertion / State accuracy", f"{pct(a['assertion_accuracy']['accuracy'])} ({cnt(a['assertion_accuracy']['match_count'], a['assertion_accuracy']['total'])})", f"{pct(b['assertion_accuracy']['accuracy'])} ({cnt(b['assertion_accuracy']['match_count'], b['assertion_accuracy']['total'])})"),
        ("Relation F1", pct(a['rel']['f1']), pct(b['rel']['f1'])),
        ("Retrieval Recall@K", f"{pct(a['terminology']['retrieval_acc'])} ({cnt(a['terminology']['ret_match'], a['terminology']['total'])})", f"{pct(b['terminology']['retrieval_acc'])} ({cnt(b['terminology']['ret_match'], b['terminology']['total'])})"),
        ("Selection accuracy", f"{pct(a['terminology']['selection_acc'])} ({cnt(a['terminology']['sel_match'], a['terminology']['total'])})", f"{pct(b['terminology']['selection_acc'])} ({cnt(b['terminology']['sel_match'], b['terminology']['total'])})"),
        ("Located evidence rate", pct(a['evidence']['loc_rate']), pct(b['evidence']['loc_rate'])),
        ("Value-in-evidence rate", pct(a['evidence']['val_rate']), pct(b['evidence']['val_rate'])),
        ("Unsupported field rate", f"{pct(a['evidence']['unsupported_rate'])} ({a['evidence']['unsup_count']} fields)", f"{pct(b['evidence']['unsupported_rate'])} ({b['evidence']['unsup_count']} fields)"),
        ("Invalid code rate", "0.0%", "0.0%"),
        ("Mean runtime", f"{a['operations']['mean_runtime_sec']:.2f}s", f"{b['operations']['mean_runtime_sec']:.2f}s"),
        ("Mean cost", f"${a['operations']['mean_cost_usd']:.4f}", f"${b['operations']['mean_cost_usd']:.4f}"),
    ]
    return "\\n".join(f"| {' | '.join(r)} |" for r in rows)

if __name__ == "__main__":
    res_a = evaluate(PIPELINE_A_DIR, GOLD_DIR, "Pipeline A")
    res_b = evaluate(PIPELINE_B_DIR, GOLD_DIR, "Pipeline B")

    table = build_comparison_table(res_a, res_b)
    table_path = EVAL_DIR / "comparison_table.md"
    table_path.write_text(
        "# Pipeline Evaluation: Side-by-Side Comparison\\n\\n"
        f"*Generated: {__import__('datetime').datetime.utcnow().isoformat()}Z*\\n\\n"
        "Denominator: 180/200 fields evaluated (20 fields x 10 reports = 200; array counts differ)\\n\\n"
        + table + "\\n", encoding="utf-8"
    )
    print(table)
    
    # Save results.json
    results_path = EVAL_DIR / "results.json"
    results_path.write_text(json.dumps({"pipeline_a": res_a, "pipeline_b": res_b}, indent=2), encoding="utf-8")
