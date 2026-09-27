import re

def normalize_ws(text):
    if text is None: return None
    if not isinstance(text, str): text = str(text)
    return " ".join(text.split())

def normalize_for_comparison(text):
    if text is None: return None
    s = str(text).lower()
    m = re.match(r"^([\d\.]+)\s*cm$", s)
    if m:
        try: return f"{float(m.group(1)) * 10:g} mm"
        except: pass
    s = re.sub(r'[\.,;:!?]+$', '', s).strip()
    return normalize_ws(s)

def normalize_to_schema(field_name: str, raw_value, context: dict):
    """
    field_name: one of the 20 schema keys
    raw_value:  literal text extracted by the pipeline
    context:    dict with any additional info, e.g. {"laterality": "left", "primary_site": "breast", "grading_system": "Nottingham"}
    returns:    normalized schema concept as a string (or None)
    """
    if raw_value is None:
        return None
        
    # We might receive a list or dict if the pipeline messed up, convert safely
    if isinstance(raw_value, list):
        if not raw_value: return None
        raw_val = str(raw_value[0])
    else:
        raw_val = str(raw_value)
        
    val_lower = raw_val.lower().strip()

    if field_name == "specimen":
        # Strip trailing "specimen", "sample", "tissue". Title-case.
        s = re.sub(r'\b(specimen|sample|tissue)s?\b', '', val_lower).strip()
        return s.capitalize() if s else raw_val.capitalize()

    elif field_name == "procedure":
        # Title-case, keep extracted phrase
        return raw_val.capitalize()

    elif field_name == "primary_tumor_site":
        s = raw_val.capitalize()
        # If the value is just an organ, prepend laterality
        organs = {"breast", "colon", "lung", "rectum", "cecum"}
        if val_lower in organs:
            lat = context.get("laterality")
            if lat and lat.lower() != "not applicable":
                s = f"{lat.capitalize()} {val_lower}"
        return s

    elif field_name == "laterality":
        return raw_val.capitalize()

    elif field_name == "histological_type":
        s = val_lower
        s = re.sub(r'\bidc\b', 'invasive ductal carcinoma', s)
        s = re.sub(r'\bnst\b', 'no special type', s)
        s = re.sub(r'\bnos\b', 'not otherwise specified', s)
        return s.capitalize()

    elif field_name == "tumor_behavior":
        s = val_lower
        if "in situ" in s or "in-situ" in s or "insitu" in s: return "In situ"
        if "invas" in s: return "Invasive"
        if "uncertain" in s or "indeterminate" in s: return "Uncertain"
        return raw_val.capitalize()

    elif field_name == "tumor_grade":
        if val_lower in ["1", "2", "3", "4", "i", "ii", "iii", "iv"]:
            system = context.get("grading_system")
            if system:
                return f"{system} Grade {raw_val}"
            return raw_val
        if "differentiated" in val_lower:
            system = context.get("grading_system")
            if system == "Nottingham":
                if "well" in val_lower: return "Nottingham Grade 1 (well differentiated)"
                if "moderate" in val_lower: return "Nottingham Grade 2 (moderately differentiated)"
                if "poor" in val_lower: return "Nottingham Grade 3 (poorly differentiated)"
        return raw_val

    elif field_name == "tumor_size":
        return raw_val

    elif field_name == "tumor_focality":
        if val_lower in ["1", "one", "single", "single lesion", "unifocal"]:
            return "Single lesion"
        if val_lower in ["2", "two", "multiple", "multifocal", "two lesions"]:
            return "Multifocal"
        if "single" in val_lower and "lesion" in val_lower:
            return "Single lesion"
        if "not mentioned" in val_lower:
            return None
        return raw_val.capitalize()

    elif field_name == "tumor_extension":
        return raw_val.capitalize()

    elif field_name == "lymphovascular_invasion":
        if "not identified" in val_lower: return "Absent"
        if "absent" in val_lower: return "Absent"
        if "present" in val_lower: return "Present"
        if "indeterminate" in val_lower: return "Indeterminate"
        if "not mentioned" in val_lower: return None
        return raw_val.capitalize()

    elif field_name == "perineural_invasion":
        if "not identified" in val_lower: return "Absent"
        if "absent" in val_lower: return "Absent"
        if "present" in val_lower: return "Present"
        if "indeterminate" in val_lower: return "Indeterminate"
        if "not mentioned" in val_lower: return None
        return raw_val.capitalize()

    elif field_name == "surgical_margins":
        if val_lower in ["negative", "clear"]:
            margin = context.get("margin")
            if margin:
                return f"Negative (closest margin {margin})"
            return "Negative"
        if val_lower == "positive": return "Positive"
        if val_lower == "close": return "Close"
        return raw_val

    elif field_name == "lymph_nodes_examined":
        return raw_val

    elif field_name == "positive_lymph_nodes":
        return raw_val

    elif field_name in ["pathologic_t", "pathologic_n", "pathologic_m"]:
        if "not mentioned" in val_lower: return None
        # pt2 -> pT2
        s = raw_val
        if s.startswith("p") or s.startswith("y"):
            # keep first letter lower, next upper
            idx = 1
            if s.startswith("yp"): idx = 2
            if len(s) > idx:
                s = s[:idx].lower() + s[idx].upper() + s[idx+1:].lower()
        return s

    return raw_val
