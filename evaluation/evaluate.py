import json
import os
import glob
import time
from pathlib import Path
from collections import defaultdict

def normalize_string(s):
    if not s: return ""
    return str(s).lower().strip()

def calc_f1(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def evaluate_pipeline(pipeline_dir, gold_dir, name="Pipeline"):
    print(f"\\n============================================================")
    print(f"  Evaluating {name}")
    print(f"============================================================")
    
    gold_files = sorted(glob.glob(os.path.join(gold_dir, "*.json")))
    if not gold_files:
        print("No gold files found.")
        return
        
    metrics = {
        'entity_tp': 0, 'entity_fp': 0, 'entity_fn': 0,  # Proxy for relation/NER field population
        'exact_value_match': 0, 'total_values': 0,
        'state_match': 0, 'total_states': 0,
        'exact_code_match': 0, 'total_codes_gold': 0, 'total_codes_pred': 0,
        'unsupported_field_count': 0,
        'invalid_code_count': 0,
        'evidence_match_count': 0,
    }
    
    # Track metrics per field
    field_metrics = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0, 'state_match': 0, 'value_match': 0, 'total': 0})
    
    discrepancies = []
    
    start_time = time.time()
    
    for gold_path in gold_files:
        basename = os.path.basename(gold_path)
        pred_path = os.path.join(pipeline_dir, basename)
        
        with open(gold_path, 'r', encoding='utf-8') as f:
            gold_data = json.load(f)
            
        if not os.path.exists(pred_path):
            print(f"[MISSING] {basename} not found in predictions.")
            continue
            
        with open(pred_path, 'r', encoding='utf-8') as f:
            pred_data = json.load(f)
            
        gold_fields = gold_data.get('annotations', {})
        pred_fields = pred_data.get('fields', {})
        
        # We will assume a "relation/entity" exists if the field has a value or codes, or state is 'present'
        for field_name in gold_fields.keys():
            g_field = gold_fields.get(field_name, {})
            p_field = pred_fields.get(field_name, {})
            
            g_val = g_field.get('value')
            g_state = g_field.get('state')
            g_codes = g_field.get('codes', [])
            
            p_val = p_field.get('value')
            p_state = p_field.get('state')
            p_codes = p_field.get('codes', [])
            
            field_metrics[field_name]['total'] += 1
            
            # Entity Recognition / Relation (Field population)
            g_populated = bool(g_val or (g_state == 'present'))
            p_populated = bool(p_val or (p_state == 'present'))
            
            if g_populated and p_populated:
                metrics['entity_tp'] += 1
                field_metrics[field_name]['tp'] += 1
            elif g_populated and not p_populated:
                metrics['entity_fn'] += 1
                field_metrics[field_name]['fn'] += 1
            elif not g_populated and p_populated:
                metrics['entity_fp'] += 1
                field_metrics[field_name]['fp'] += 1
                
            # State / Assertion matching
            if g_state:
                metrics['total_states'] += 1
                if g_state == p_state:
                    metrics['state_match'] += 1
                    field_metrics[field_name]['state_match'] += 1
                    
            # Value matching (exact normalized)
            if g_val:
                metrics['total_values'] += 1
                if normalize_string(g_val) == normalize_string(p_val):
                    metrics['exact_value_match'] += 1
                    field_metrics[field_name]['value_match'] += 1
            
            # Terminology matching
            # Gold uses a dict: {'ICD-O-3-M': '8500/3'}
            # Pred uses a dict: {'ICD-O-3': 'C50.4'}
            g_code_ids = set(g_codes.values()) if isinstance(g_codes, dict) else set()
            p_code_ids = set(p_codes.values()) if isinstance(p_codes, dict) else set()
            
            if g_code_ids:
                metrics['total_codes_gold'] += len(g_code_ids)
            if p_code_ids:
                metrics['total_codes_pred'] += len(p_code_ids)
                
            for pid in p_code_ids:
                if pid in g_code_ids:
                    metrics['exact_code_match'] += 1
                    
            # Discrepancy capture for error analysis
            if (g_val and normalize_string(g_val) != normalize_string(p_val)) or (g_state and g_state != p_state) or (g_code_ids != p_code_ids):
                if len(discrepancies) < 20: # keep a pool to sample from
                    discrepancies.append({
                        'report': basename,
                        'field': field_name,
                        'gold_value': g_val,
                        'gold_state': g_state,
                        'gold_codes': list(g_code_ids),
                        'pred_value': p_val,
                        'pred_state': p_state,
                        'pred_codes': list(p_code_ids),
                        'evidence': p_field.get('evidence', '')
                    })
                    
    end_time = time.time()
    runtime = end_time - start_time
    
    # Compute aggregates
    p, r, f1 = calc_f1(metrics['entity_tp'], metrics['entity_fp'], metrics['entity_fn'])
    state_acc = metrics['state_match'] / metrics['total_states'] if metrics['total_states'] else 0
    val_acc = metrics['exact_value_match'] / metrics['total_values'] if metrics['total_values'] else 0
    code_acc = metrics['exact_code_match'] / metrics['total_codes_pred'] if metrics['total_codes_pred'] else 0
    code_recall = metrics['exact_code_match'] / metrics['total_codes_gold'] if metrics['total_codes_gold'] else 0
    
    print(f"\\n--- AGGREGATE METRICS ({name}) ---")
    print(f"Entity/Relation (Field Populated): Precision={p:.3f}, Recall={r:.3f}, F1={f1:.3f}")
    print(f"State/Assertion Accuracy:          {state_acc:.3f} ({metrics['state_match']}/{metrics['total_states']})")
    print(f"Exact Normalized Value Accuracy:   {val_acc:.3f} ({metrics['exact_value_match']}/{metrics['total_values']})")
    print(f"Terminology Exact Code Accuracy:   {code_acc:.3f} ({metrics['exact_code_match']}/{metrics['total_codes_pred']})")
    print(f"Terminology Recall:                {code_recall:.3f} ({metrics['exact_code_match']}/{metrics['total_codes_gold']})")
    print(f"Runtime per report:                {runtime / len(gold_files):.4f} seconds (simulated ops)")
    
    print(f"\\n--- SAMPLE DISCREPANCIES ---")
    for i, d in enumerate(discrepancies[:5]):
        print(f"[{i+1}] {d['report']} - {d['field']}")
        print(f"    Gold: value='{d['gold_value']}', state='{d['gold_state']}', codes={d['gold_codes']}")
        print(f"    Pred: value='{d['pred_value']}', state='{d['pred_state']}', codes={d['pred_codes']}")
        print(f"    Evid: '{d['evidence']}'")

if __name__ == "__main__":
    evaluate_pipeline('outputs/pipeline_a', 'data/gold', "Pipeline A (Classical NLP)")
    evaluate_pipeline('outputs/pipeline_b', 'data/gold', "Pipeline B (LLM + Retrieval)")
