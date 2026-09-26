import json
import glob
import re

print("=== ISSUE 1: BIOMARKERS VERIFICATION ===")
print("report_id | biomarkers_mentioned_in_text | biomarkers_in_gold | match (Y/N)")
for i in range(1, 11):
    rid = f"report_{i:03d}"
    
    with open(f"data/raw/{rid}.txt") as f:
        text = f.read().lower()
        
    mentioned = set()
    if "er" in text or "estrogen" in text: mentioned.add("ER")
    if "pr" in text or "progesterone" in text: mentioned.add("PR")
    if "her2" in text: mentioned.add("HER2")
    if "kras" in text: mentioned.add("KRAS")
    if "egfr" in text: mentioned.add("EGFR")
    if "braf" in text: mentioned.add("BRAF")
    if "nras" in text: mentioned.add("NRAS")
    if "mmr" in text: mentioned.add("MMR")
    
    with open(f"data/gold/{rid}.json") as f:
        gold = json.load(f)
    
    # Actually some reports might not test ER, PR, HER2 but just mention "Breast cancer -- KRAS not tested or applicable"
    # Wait, if it says "KRAS not tested or applicable", it's mentioned.
    # The gold currently has "KRAS" as "not applicable".
    # User says: "If the gold has entries for assays that are NOT mentioned in the report, remove them"
    # So if it's explicitly mentioned as "not applicable", it IS mentioned.
    # But let's count actual entries in gold vs our regex count.
    
    gold_biomarkers = gold.get("annotations", {}).get("biomarkers", [])
    gold_count = len(gold_biomarkers)
    # let's be more precise with mentioned
    text_upper = text.upper()
    mentioned = set()
    for b in ["ER", "PR", "HER2", "KRAS", "EGFR", "BRAF", "NRAS", "MMR"]:
        if b in text_upper:
            mentioned.add(b)
    
    text_count = len(mentioned)
    match = "Y" if text_count == gold_count else "N"
    print(f"{rid} | {text_count} | {gold_count} | {match}")
    if match == "N":
        print(f"  -> text: {mentioned}")
        print(f"  -> gold: {[b['assay'] for b in gold_biomarkers]}")

print("\n=== ISSUE 2: STATE BREAKDOWN FOR report_001 ===")
for i in range(1, 3):
    rid = f"report_{i:03d}"
    with open(f"data/gold/{rid}.json") as f:
        gold = json.load(f)["annotations"]
    print(f"\nReport: {rid}")
    for k, v in gold.items():
        if isinstance(v, list):
            print(f"{k} | (array len: {len(v)})")
        else:
            print(f"{k} | {v.get('state')} | {v.get('value')}")

print("\n=== ISSUE 3: STATE MISMATCH DIAGNOSIS ===")
mismatches = []
for i in range(1, 11):
    rid = f"report_{i:03d}"
    with open(f"data/gold/{rid}.json") as f:
        gold = json.load(f)["annotations"]
    try:
        with open(f"outputs/pipeline_a/{rid}.json") as f:
            pred_a = json.load(f)["fields"]
    except FileNotFoundError:
        continue
    
    for fname, gval in gold.items():
        if isinstance(gval, list): continue
        pval = pred_a.get(fname, {})
        gs = gval.get("state")
        ps = pval.get("state")
        if gs and ps and gs != ps:
            mismatches.append(f"{rid} | {fname} | gold='{gs}' | pipeline='{ps}'")
            
print(f"Found {len(mismatches)} state mismatches. First 5:")
for m in mismatches[:5]:
    print(m)

print("\n=== ISSUE 5: TERMINOLOGY CODES PIPELINE A ===")
for i in range(1, 2):
    rid = f"report_{i:03d}"
    with open(f"data/gold/{rid}.json") as f:
        gold = json.load(f)["annotations"]
    with open(f"outputs/pipeline_a/{rid}.json") as f:
        pred_a = json.load(f)["fields"]
    
    gold_codes = []
    pred_codes = []
    for fname, gval in gold.items():
        if isinstance(gval, list): continue
        if gval.get("codes"): gold_codes.append((fname, gval["codes"]))
        if pred_a.get(fname, {}).get("codes"): pred_codes.append((fname, pred_a[fname]["codes"]))
        
    print("Gold codes in report_001:", gold_codes)
    print("Pred codes in report_001:", pred_codes)
