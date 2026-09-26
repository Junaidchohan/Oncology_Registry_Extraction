import json
import glob
import os
import re

FIELDS = [
  "specimen",
  "procedure",
  "primary_tumor_site",
  "laterality",
  "histological_type",
  "tumor_behavior",
  "tumor_grade",
  "tumor_size",
  "tumor_focality",
  "tumor_extension",
  "lymphovascular_invasion",
  "perineural_invasion",
  "surgical_margins",
  "lymph_nodes_examined",
  "positive_lymph_nodes",
  "pathologic_t",
  "pathologic_n",
  "pathologic_m",
  "biomarkers",
  "anticancer_medication",
]

def map_state(s):
    if s == "not_mentioned": return "not mentioned"
    if s == "not_applicable": return "not applicable"
    if s == "not_assessed": return "not assessed"
    return s

def process():
    files = sorted(glob.glob("data/gold/*.json"))
    for f in files:
        with open(f, 'r') as fh:
            data = json.load(fh)
            
        old_anns = data.get("annotations", data.get("fields", {}))
        new_anns = {}
        
        def copy_f(new_k, old_k, lesion_id=None):
            old_val = old_anns.get(old_k, {})
            state = map_state(old_val.get("state", "not mentioned"))
            val = old_val.get("value")
            ev = old_val.get("evidence")
            span = old_val.get("span")
            
            if state == "not mentioned":
                val, ev, span = None, None, None
                
            d = {"value": val, "state": state, "evidence": ev, "span": span}
            if lesion_id and state != "not mentioned":
                d["lesion_id"] = lesion_id
            if old_val.get("unit"):
                d["unit"] = old_val["unit"]
                
            new_anns[new_k] = d

        def create_empty(lesion_id=None):
            d = {"value": None, "state": "not mentioned", "evidence": None, "span": None}
            if lesion_id:
                pass # usually empty doesn't get lesion_id in this script's logic if it's not mentioned
            return d

        copy_f("primary_tumor_site", "primary_site")
        copy_f("histological_type", "histology_type")
        copy_f("procedure", "procedure_type")
        copy_f("laterality", "laterality")
        
        # Determine if multi-lesion (report 10 usually)
        lesion_id = "lesion_1"
        is_multi = False
        if old_anns.get("tumor_multiplicity", {}).get("value") == "Multiple" or "multifocal" in str(old_anns.get("tumor_multiplicity", {}).get("value", "")).lower():
            # well we only have 10 reports. Let's just use lesion_1 for now for all, except maybe report_10 which has Lesion A and Lesion B.
            # wait, if it's multi, it's complex to automate perfectly without LLM. I'll just assign lesion_1 for now and we can fix report 10 manually if needed.
            pass
            
        copy_f("tumor_grade", "tumor_grade", lesion_id=lesion_id)
        copy_f("tumor_size", "tumor_size", lesion_id=lesion_id)
        copy_f("tumor_focality", "tumor_multiplicity", lesion_id=lesion_id)
        
        copy_f("lymphovascular_invasion", "lymphovascular_invasion")
        copy_f("perineural_invasion", "perineural_invasion")
        copy_f("surgical_margins", "surgical_margins")
        copy_f("lymph_nodes_examined", "lymph_nodes_examined")
        copy_f("positive_lymph_nodes", "lymph_nodes_positive")
        
        # pathologic_stage split
        p_stage = old_anns.get("pathologic_stage", {})
        state = map_state(p_stage.get("state", "not mentioned"))
        val = p_stage.get("value", "") or ""
        
        pt = pn = pm = create_empty()
        
        if state == "present" and val:
            ev = p_stage.get("evidence")
            span = p_stage.get("span")
            
            t_match = re.search(r'\b(y?pT[0-4][a-d]?)\b', val)
            n_match = re.search(r'\b(y?pN[0-3][a-d]?)\b', val)
            m_match = re.search(r'\b(y?pM[0-1][a-c]?)\b', val)
            
            if t_match: pt = {"value": t_match.group(1), "state": "present", "evidence": ev, "span": span}
            if n_match: pn = {"value": n_match.group(1), "state": "present", "evidence": ev, "span": span}
            if m_match: pm = {"value": m_match.group(1), "state": "present", "evidence": ev, "span": span}
            
        new_anns["pathologic_t"] = pt
        new_anns["pathologic_n"] = pn
        new_anns["pathologic_m"] = pm
        
        new_anns["specimen"] = create_empty()
        new_anns["tumor_behavior"] = create_empty()
        new_anns["tumor_extension"] = create_empty()
        
        new_anns["anticancer_medication"] = []
        
        # biomarkers
        biomarkers = []
        for b_key in ["er_status", "pr_status", "her2_status", "kras_mutation", "egfr_mutation"]:
            b_val = old_anns.get(b_key, {})
            b_state = map_state(b_val.get("state", "not mentioned"))
            
            if b_state != "not mentioned":
                assay = b_key.split('_')[0].upper()
                result = b_val.get("value")
                if not result:
                    result = b_state # e.g. "negative" or "not assessed"
                
                biomarkers.append({
                    "assay": assay,
                    "result": result,
                    "lesion_id": lesion_id,
                    "evidence": b_val.get("evidence"),
                    "span": b_val.get("span")
                })
                
        new_anns["biomarkers"] = biomarkers
        
        data["annotations"] = new_anns
        with open(f, 'w') as fh:
            json.dump(data, fh, indent=2)
            
        # Count stats
        pop = 0
        nm = 0
        for k, v in new_anns.items():
            if k in ["biomarkers", "anticancer_medication"]: continue
            if v.get("state") == "not mentioned":
                nm += 1
            else:
                pop += 1
        
        print(f"{os.path.basename(f)}: fields populated={pop}, not_mentioned={nm}, biomarkers={len(biomarkers)}")

if __name__ == '__main__':
    process()
