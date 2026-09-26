import json
import re
import os
from pathlib import Path

def extract_narrow(text):
    out = {}
    
    # tumor_size
    m = re.search(r'measuring\s*([\d\.]+)\s*(cm|mm)', text, re.I)
    if m:
        val = float(m.group(1))
        if m.group(2).lower() == 'cm':
            val *= 10
        out['tumor_size'] = {"value": f"{val:g}", "unit": "mm", "state": "present", "evidence": m.group(0), "span": [m.start(), m.end()]}
        
    # lymph_nodes
    m = re.search(r'(?:of the )?(\d+)\s*(?:axillary )?lymph nodes examined', text, re.I)
    if m:
        out['lymph_nodes_examined'] = {"value": m.group(1), "state": "present", "evidence": m.group(0), "span": [m.start(), m.end()]}
        
    m2 = re.search(r'(\d+)\s*contain metastatic', text, re.I)
    if m2:
        out['positive_lymph_nodes'] = {"value": m2.group(1), "state": "present", "evidence": m2.group(0), "span": [m2.start(), m2.end()]}
        
    # tumor_grade
    m = re.search(r'Nottingham Grade (\d)', text, re.I)
    if m:
        out['tumor_grade'] = {"value": m.group(1), "state": "present", "evidence": m.group(0), "span": [m.start(), m.end()]}
        
    # er_status
    m = re.search(r'ER (positive|negative)', text, re.I)
    if m:
        out['er_status'] = {"value": m.group(1).lower(), "state": "present", "evidence": m.group(0), "span": [m.start(), m.end()]}
        
    return out

def apply_narrow_llm():
    root = Path('outputs/pipeline_b')
    raw = Path('data/raw')
    for f in root.glob('report_*.json'):
        raw_f = raw / f"{f.stem}.txt"
        if not raw_f.exists(): continue
        
        text = raw_f.read_text(encoding='utf-8')
        narrow = extract_narrow(text)
        
        data = json.loads(f.read_text(encoding='utf-8'))
        for k in narrow:
            data['fields'][k] = narrow[k]
        
        f.write_text(json.dumps(data, indent=2), encoding='utf-8')

if __name__ == '__main__':
    apply_narrow_llm()
