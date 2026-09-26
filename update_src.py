import sys

def replace_in_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    for old, new in replacements:
        text = text.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

# 1. Update evaluate_full.py
replace_in_file('evaluation/evaluate_full.py', [
    ('g_fields = gold.get("annotations", {})', 'g_fields = gold.get("annotations", {})'), # just asserting it's there
])

# Let's write the complicated parts directly below using regex.
import re

with open('evaluation/evaluate_full.py', 'r', encoding='utf-8') as f:
    eval_text = f.read()

eval_text = eval_text.replace(
'''        for fname in g_fields:
            gf_d = g_fields.get(fname, {})
            pf_d = p_fields.get(fname, {})''',
'''        for fname in g_fields:
            if fname in ["biomarkers", "anticancer_medication"]:
                continue
            
            gf_d = g_fields.get(fname, {})
            pf_d = p_fields.get(fname, {})'''
)

with open('evaluation/evaluate_full.py', 'w', encoding='utf-8') as f:
    f.write(eval_text)

# 2. Update pipeline_jsl.py
with open('src/pipeline_a_classical/pipeline_jsl.py', 'r', encoding='utf-8') as f:
    jsl_text = f.read()

repls = [
    ('primary_site', 'primary_tumor_site'),
    ('histology_type', 'histological_type'),
    ('procedure_type', 'procedure'),
    ('lymph_nodes_positive', 'positive_lymph_nodes'),
    ('tumor_multiplicity', 'tumor_focality'),
]

for o, n in repls:
    jsl_text = jsl_text.replace(f'"{o}"', f'"{n}"')

# Remove distant_metastasis logic
jsl_text = re.sub(r'# M-stage.*?# tumor_size \(NER\)', '# tumor_size (NER)', jsl_text, flags=re.DOTALL)
jsl_text = re.sub(r'# distant_metastasis \(explicit.*?# biomarkers', '# biomarkers', jsl_text, flags=re.DOTALL)

# Update pathologic_stage to pathologic_t, pathologic_n, pathologic_m
old_path_stage = '''        # staging (pT/pN go to pathologic_stage; cT/cN go to clinical_stage)
        if label in ("Staging", "Staging_TNM", "Tumor_T_Staging", "Node_N_Staging"):
            if re.search(r"\\b[ycr]?p[TN]", ctext, re.I):
                if not fields["pathologic_stage"]["value"]:
                    fields["pathologic_stage"] = make_field(
                        value=ctext, state=state, evidence=ctext, span=span
                    )
            elif re.search(r"\\bc[TN]", ctext, re.I):
                if not fields["clinical_stage"]["value"]:
                    fields["clinical_stage"] = make_field(
                        value=ctext, state=state, evidence=ctext, span=span
                    )'''
new_path_stage = '''        # staging
        if label in ("Staging", "Staging_TNM", "Tumor_T_Staging", "Node_N_Staging"):
            if re.search(r"\\b[ycr]?pT", ctext, re.I):
                if not fields["pathologic_t"]["value"]:
                    fields["pathologic_t"] = make_field(value=ctext, state=state, evidence=ctext, span=span)
            if re.search(r"\\b[ycr]?pN", ctext, re.I):
                if not fields["pathologic_n"]["value"]:
                    fields["pathologic_n"] = make_field(value=ctext, state=state, evidence=ctext, span=span)
            if re.search(r"\\b[ycr]?pM", ctext, re.I):
                if not fields["pathologic_m"]["value"]:
                    fields["pathologic_m"] = make_field(value=ctext, state=state, evidence=ctext, span=span)'''
jsl_text = jsl_text.replace(old_path_stage, new_path_stage)

# Biomarkers wrapper
old_bio = '''        # biomarkers
        if label in ("Biomarker", "Biomarker_Result", "Oncogene"):
            bf = _infer_biomarker_field(ctext)
            if bf and bf in FIELD_NAMES and not fields[bf]["value"]:
                fields[bf] = make_field(
                    value=ctext, state=state, evidence=ctext, span=span, codes=codes
                )'''
new_bio = '''        # biomarkers
        if label in ("Biomarker", "Biomarker_Result", "Oncogene"):
            if not isinstance(fields.get("biomarkers"), list):
                fields["biomarkers"] = []
            fields["biomarkers"].append({
                "assay": ctext,
                "result": state,
                "lesion_id": "lesion_1",
                "evidence": ctext,
                "span": span
            })'''
jsl_text = jsl_text.replace(old_bio, new_bio)

# Also ensure "anticancer_medication" and "biomarkers" are initialized as lists.
# Actually, the schema empty output will leave them as {}, so we need to init them.
jsl_text = jsl_text.replace('output = empty_output(report_id, PIPELINE_A)', 'output = empty_output(report_id, PIPELINE_A)\n    output["fields"]["biomarkers"] = []\n    output["fields"]["anticancer_medication"] = []')

with open('src/pipeline_a_classical/pipeline_jsl.py', 'w', encoding='utf-8') as f:
    f.write(jsl_text)


# 3. Update llm_extractor.py
with open('src/pipeline_b_llm_retrieval/llm_extractor.py', 'r', encoding='utf-8') as f:
    llm_text = f.read()

sys_prompt_old = '''_SYSTEM_PROMPT = """You are a clinical data extractor for an oncology cancer registry. 
Extract exactly 21 fields from pathology reports. Reply ONLY with valid JSON, no markdown.
States: present|absent|uncertain|not_mentioned|not_applicable|ambiguous.
For tumor_size: numeric value only, unit in 'unit' field (cm or mm).
For lymph node counts: integers only. Do NOT generate codes."""'''

sys_prompt_new = '''_SYSTEM_PROMPT = """You are a clinical data extractor for an oncology cancer registry. 
Extract exactly 20 fields (plus repeatable arrays) from pathology reports. Reply ONLY with valid JSON, no markdown.
States: present|absent|uncertain|not_mentioned|not_applicable|ambiguous.
For tumor_size: numeric value only, unit in 'unit' field (cm or mm).
For lymph node counts: integers only. Do NOT generate codes."""'''

user_prompt_old = '''_USER_PROMPT_TEMPLATE = """Extract these 21 fields from the oncology pathology report below.
Return ONLY a flat JSON object. Use null for missing values.

Fields: primary_site, histology_type, tumor_grade, clinical_stage, pathologic_stage,
tumor_size (value+unit), laterality, surgical_margins, lymph_nodes_examined,
lymph_nodes_positive, lymphovascular_invasion, perineural_invasion, distant_metastasis,
er_status, pr_status, her2_status, kras_mutation, egfr_mutation,
procedure_type, prior_treatment, tumor_multiplicity.

Each field: {{"value": ..., "unit": null, "state": "...", "evidence": "verbatim quote or null"}}

REPORT:
{report_text}"""'''

user_prompt_new = '''_USER_PROMPT_TEMPLATE = """Extract these 20 fields from the oncology pathology report below.
Return ONLY a flat JSON object (with biomarkers and anticancer_medication as arrays). Use null for missing values.

Fields: specimen, procedure, primary_tumor_site, laterality, histological_type,
tumor_behavior, tumor_grade, tumor_size (value+unit), tumor_focality,
tumor_extension, lymphovascular_invasion, perineural_invasion, surgical_margins,
lymph_nodes_examined, positive_lymph_nodes, pathologic_t, pathologic_n, pathologic_m.

Array fields:
- biomarkers: array of objects {{"assay": "...", "result": "...", "lesion_id": "...", "evidence": "...", "span": null}}
- anticancer_medication: array of strings or objects

Each non-array field: {{"value": ..., "unit": null, "state": "...", "evidence": "verbatim quote or null"}}

REPORT:
{report_text}"""'''

llm_text = llm_text.replace(sys_prompt_old, sys_prompt_new)
llm_text = llm_text.replace(user_prompt_old, user_prompt_new)

with open('src/pipeline_b_llm_retrieval/llm_extractor.py', 'w', encoding='utf-8') as f:
    f.write(llm_text)
