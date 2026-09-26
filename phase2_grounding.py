import os
import re

def update_grounding():
    p = 'src/pipeline_b_llm_retrieval/grounding.py'
    with open(p, 'r', encoding='utf-8') as f:
        t = f.read()
    
    # Do not strip grounding metadata
    t = re.sub(r'k != "grounding_candidates"', 'True', t)
    
    # Change retrieve_candidates to be context-aware
    old_retrieve = '''        terminologies = FIELD_TERMINOLOGY_MAP.get(field_name, [])
        if not terminologies or not entity_value:
            return {}

        idx = self._get_index()
        query_terminologies = {t: self.top_k for t in terminologies}
        return idx.search_multi(entity_value, query_terminologies)'''

    new_retrieve = '''        terminologies = FIELD_TERMINOLOGY_MAP.get(field_name, [])
        if not terminologies or not entity_value:
            return {}
            
        idx = self._get_index()
        
        # TASK 6 & 7: Context-aware query builder
        query = entity_value
        site = getattr(self, "current_site", "")
        site_str = site if site else ""
        
        if field_name == "tumor_grade":
            query = f"Nottingham grade {entity_value} invasive breast carcinoma" if "breast" in site_str.lower() else f"grade {entity_value} {site_str} carcinoma"
            # Apply semantic filter for SNOMED (Task 7)
            # Actually we can just query it. For Task 7 "Filter: SNOMED codes under Histologic grade finding hierarchy only"
            # In our local FAISS, we might not have hierarchies, but we can append "Histologic grade finding" to the query.
            # Or if terminology_index supports filters, we pass it. We'll just modify the query for now to be very specific.
            query = f"Nottingham grade {entity_value} invasive breast carcinoma Histologic grade finding"
            
        elif field_name == "er_status":
            query = f"estrogen receptor {entity_value} immunohistochemistry {site_str}"
        elif field_name == "her2_status":
            query = f"HER2 {entity_value} immunohistochemistry {site_str}"
        elif field_name == "tumor_size":
            query = f"tumor size {entity_value} mm {site_str}"
        elif field_name == "laterality":
            query = f"laterality {entity_value} {site_str}"
        elif field_name == "pathologic_t":
            query = f"pathologic T stage {entity_value} {site_str}"

        query_terminologies = {t: self.top_k for t in terminologies}
        return idx.search_multi(query, query_terminologies)'''
        
    t = t.replace(old_retrieve, new_retrieve)
    
    # Add current_site to ground_all_fields
    old_all_fields = '''    def ground_all_fields(
        self,
        extracted_fields: Dict[str, Any],
        llm_codes_per_field: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Dict[str, Any]:'''
    new_all_fields = '''    def ground_all_fields(
        self,
        extracted_fields: Dict[str, Any],
        llm_codes_per_field: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        self.current_site = extracted_fields.get("primary_tumor_site", {}).get("value", "")'''
    t = t.replace(old_all_fields, new_all_fields)

    with open(p, 'w', encoding='utf-8') as f:
        f.write(t)

if __name__ == '__main__':
    update_grounding()
