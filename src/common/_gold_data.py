# _gold_data.py — gold annotation data (auto-generated, do not edit manually)

GOLD = {}

GOLD["report_001"] = {
    "report_id": "report_001",
    "cancer_type": "Breast",
    "procedure": "Modified radical mastectomy",
    "annotations": {
        "primary_site": {"value": "Left breast, upper outer quadrant", "unit": None, "state": "present", "evidence": "firm, stellate, grey-white mass... in the upper outer quadrant", "span": [318, 376], "codes": {"ICD-O-3": "C50.4"}},
        "histology_type": {"value": "Invasive ductal carcinoma, NST (no special type)", "unit": None, "state": "present", "evidence": "infiltrating ductal carcinoma (IDC), no special type (NST)", "span": [612, 660], "codes": {"ICD-O-3-M": "8500/3"}},
        "tumor_grade": {"value": "Nottingham Grade 2", "unit": None, "state": "present", "evidence": "Nottingham Grade 2 (tubule formation 3, nuclear pleomorphism 2, mitotic count 1; score 6/9)", "span": [662, 750], "codes": {}},
        "clinical_stage": {"value": "Not mentioned", "unit": None, "state": "not_mentioned", "evidence": None, "span": None, "codes": {}},
        "pathologic_stage": {"value": "pT2 pN1a pM0 -- Stage IIB", "unit": None, "state": "present", "evidence": "Pathologic stage: pT2 pN1a pM0 (AJCC 8th edition) -- Stage IIB", "span": [1350, 1412], "codes": {"AJCC": "Stage IIB"}},
        "tumor_size": {"value": "2.3", "unit": "cm", "state": "present", "evidence": "mass measuring 2.3 x 2.1 x 1.8 cm", "span": [307, 340], "codes": {}},
        "laterality": {"value": "Left", "unit": None, "state": "present", "evidence": "Left modified radical mastectomy specimen", "span": [241, 280], "codes": {}},
        "surgical_margins": {"value": "Negative (closest margin 2.0 cm, deep)", "unit": "cm", "state": "present", "evidence": "all other margins are negative", "span": [770, 795], "codes": {}},
        "lymph_nodes_examined": {"value": "18", "unit": None, "state": "present", "evidence": "Of the 18 axillary lymph nodes examined", "span": [797, 835], "codes": {}},
        "lymph_nodes_positive": {"value": "4", "unit": None, "state": "present", "evidence": "4 contain metastatic carcinoma", "span": [836, 865], "codes": {}},
        "lymphovascular_invasion": {"value": "Present", "unit": None, "state": "present", "evidence": "Lymphovascular invasion is identified within the tumor periphery", "span": [751, 812], "codes": {}},
        "perineural_invasion": {"value": "Absent", "unit": None, "state": "absent", "evidence": "No perineural invasion is seen", "span": [753, 782], "codes": {}},
        "distant_metastasis": {"value": "pM0 -- no distant metastasis", "unit": None, "state": "absent", "evidence": "pT2 pN1a pM0", "span": [1370, 1385], "codes": {}},
        "er_status": {"value": "Positive (Allred 8/8, >95%, 3+)", "unit": None, "state": "present", "evidence": "ER positive (Allred score 8/8, >95% cells, 3+ intensity)", "span": [955, 1010], "codes": {}},
        "pr_status": {"value": "Positive (Allred 6/8, 60%, 2+)", "unit": None, "state": "present", "evidence": "PR positive (Allred score 6/8, 60% cells, 2+ intensity)", "span": [1011, 1062], "codes": {}},
        "her2_status": {"value": "Negative (1+ IHC)", "unit": None, "state": "absent", "evidence": "HER2 score 1+ (negative by IHC)", "span": [1063, 1094], "codes": {}},
        "kras_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Breast cancer -- KRAS not tested or applicable", "span": None, "codes": {}},
        "egfr_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Breast cancer -- EGFR not tested or applicable", "span": None, "codes": {}},
        "procedure_type": {"value": "Modified radical mastectomy", "unit": None, "state": "present", "evidence": "Left modified radical mastectomy", "span": [241, 270], "codes": {"CPT": "19307"}},
        "prior_treatment": {"value": "None reported", "unit": None, "state": "absent", "evidence": "No prior breast surgery", "span": [72, 92], "codes": {}},
        "tumor_multiplicity": {"value": "Single lesion", "unit": None, "state": "absent", "evidence": "a firm, stellate, grey-white mass (single mass described)", "span": [295, 320], "codes": {}}
    }
}

GOLD["report_002"] = {
    "report_id": "report_002",
    "cancer_type": "Colorectal",
    "procedure": "Sigmoid colectomy",
    "annotations": {
        "primary_site": {"value": "Sigmoid colon", "unit": None, "state": "present", "evidence": "a 4.5 cm mass at the sigmoid colon", "span": [96, 130], "codes": {"ICD-O-3": "C18.7"}},
        "histology_type": {"value": "Colorectal adenocarcinoma", "unit": None, "state": "present", "evidence": "moderately differentiated (Grade 2) colorectal adenocarcinoma", "span": [510, 570], "codes": {"ICD-O-3-M": "8140/3"}},
        "tumor_grade": {"value": "Grade 2 (moderately differentiated)", "unit": None, "state": "present", "evidence": "moderately differentiated (Grade 2)", "span": [510, 542], "codes": {}},
        "clinical_stage": {"value": "Not mentioned (CT showed no distant metastases pre-op)", "unit": None, "state": "not_mentioned", "evidence": "CT chest/abdomen/pelvis showed no distant metastases", "span": [128, 185], "codes": {}},
        "pathologic_stage": {"value": "pT3 pN1b pM0 -- Stage IIIB", "unit": None, "state": "present", "evidence": "Pathologic stage: pT3 pN1b pM0 (AJCC 8th edition) -- Stage IIIB", "span": [1210, 1275], "codes": {"AJCC": "Stage IIIB"}},
        "tumor_size": {"value": "4.5", "unit": "cm", "state": "present", "evidence": "ulcerated, fungating tumor measuring 4.5 x 3.8 x 1.2 cm", "span": [339, 395], "codes": {}},
        "laterality": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Sigmoid colon -- laterality not applicable for colon", "span": None, "codes": {}},
        "surgical_margins": {"value": "Negative (CRM 2.5 mm)", "unit": "mm", "state": "present", "evidence": "circumferential radial margin (CRM) is negative (closest point 2.5 mm)", "span": [662, 715], "codes": {}},
        "lymph_nodes_examined": {"value": "24", "unit": None, "state": "present", "evidence": "Of 24 lymph nodes examined", "span": [718, 742], "codes": {}},
        "lymph_nodes_positive": {"value": "3", "unit": None, "state": "present", "evidence": "3 are positive for metastatic adenocarcinoma (pN1b)", "span": [743, 790], "codes": {}},
        "lymphovascular_invasion": {"value": "Present", "unit": None, "state": "present", "evidence": "Lymphovascular invasion is present", "span": [580, 614], "codes": {}},
        "perineural_invasion": {"value": "Present (2 foci)", "unit": None, "state": "present", "evidence": "Perineural invasion is identified in 2 foci", "span": [615, 655], "codes": {}},
        "distant_metastasis": {"value": "Absent", "unit": None, "state": "absent", "evidence": "No distant metastatic disease was identified in the specimen; CT confirms no metastases", "span": [791, 880], "codes": {}},
        "er_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- ER not applicable", "span": None, "codes": {}},
        "pr_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- PR not applicable", "span": None, "codes": {}},
        "her2_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- HER2 not applicable", "span": None, "codes": {}},
        "kras_mutation": {"value": "Mutant (p.G12D, codon 12)", "unit": None, "state": "present", "evidence": "KRAS mutation detected (p.G12D, codon 12)", "span": [882, 920], "codes": {"HGVS": "KRAS:p.G12D"}},
        "egfr_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- EGFR not routinely tested", "span": None, "codes": {}},
        "procedure_type": {"value": "Sigmoid colectomy", "unit": None, "state": "present", "evidence": "Sigmoid colectomy specimen", "span": [215, 240], "codes": {"CPT": "44210"}},
        "prior_treatment": {"value": "None reported", "unit": None, "state": "absent", "evidence": "No prior treatment mentioned in clinical history", "span": None, "codes": {}},
        "tumor_multiplicity": {"value": "Single lesion", "unit": None, "state": "absent", "evidence": "single ulcerated fungating tumor described", "span": [330, 360], "codes": {}}
    }
}

GOLD["report_003"] = {
    "report_id": "report_003",
    "cancer_type": "Lung",
    "procedure": "CT-guided core needle biopsy",
    "annotations": {
        "primary_site": {"value": "Right upper lobe, lung", "unit": None, "state": "present", "evidence": "3.1 cm spiculated right upper lobe mass", "span": [130, 165], "codes": {"ICD-O-3": "C34.1"}},
        "histology_type": {"value": "Pulmonary adenocarcinoma", "unit": None, "state": "present", "evidence": "consistent with pulmonary adenocarcinoma", "span": [510, 545], "codes": {"ICD-O-3-M": "8140/3"}},
        "tumor_grade": {"value": "Moderately differentiated", "unit": None, "state": "present", "evidence": "Pulmonary adenocarcinoma, moderately differentiated", "span": [905, 950], "codes": {}},
        "clinical_stage": {"value": "cT2a cN2 cM1b -- Stage IVA", "unit": None, "state": "present", "evidence": "Clinical stage: cT2a cN2 cM1b -- Stage IVA (brain metastases per PET/CT)", "span": [880, 945], "codes": {"AJCC": "Stage IVA"}},
        "pathologic_stage": {"value": "Not applicable (biopsy only)", "unit": None, "state": "not_applicable", "evidence": "CT-guided core biopsy -- full pathologic staging not possible", "span": None, "codes": {}},
        "tumor_size": {"value": "3.1", "unit": "cm", "state": "present", "evidence": "3.1 cm spiculated right upper lobe mass", "span": [130, 165], "codes": {}},
        "laterality": {"value": "Right", "unit": None, "state": "present", "evidence": "right upper lobe mass", "span": [142, 158], "codes": {}},
        "surgical_margins": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core needle biopsy -- margins not assessable", "span": None, "codes": {}},
        "lymph_nodes_examined": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy only -- lymph nodes not sampled", "span": None, "codes": {}},
        "lymph_nodes_positive": {"value": "Ipsilateral mediastinal adenopathy (imaging)", "unit": None, "state": "present", "evidence": "ipsilateral mediastinal lymphadenopathy", "span": [163, 199], "codes": {}},
        "lymphovascular_invasion": {"value": "Not assessable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy -- LVI not assessable", "span": None, "codes": {}},
        "perineural_invasion": {"value": "Not assessable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy -- PNI not assessable", "span": None, "codes": {}},
        "distant_metastasis": {"value": "Present (brain metastases)", "unit": None, "state": "present", "evidence": "multiple FDG-avid brain lesions (up to 1.2 cm)", "span": [201, 245], "codes": {"ICD-O-3": "C71.9"}},
        "er_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Pulmonary adenocarcinoma -- ER not applicable", "span": None, "codes": {}},
        "pr_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Pulmonary adenocarcinoma -- PR not applicable", "span": None, "codes": {}},
        "her2_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Pulmonary adenocarcinoma -- HER2 not applicable", "span": None, "codes": {}},
        "kras_mutation": {"value": "Wild-type", "unit": None, "state": "absent", "evidence": "KRAS wild-type", "span": [720, 736], "codes": {}},
        "egfr_mutation": {"value": "Exon 19 deletion (Del E746-A750)", "unit": None, "state": "present", "evidence": "EGFR exon 19 deletion detected (Del E746-A750)", "span": [700, 750], "codes": {"HGVS": "EGFR:p.E746_A750del"}},
        "procedure_type": {"value": "CT-guided core needle biopsy", "unit": None, "state": "present", "evidence": "CT-guided core needle biopsy of the lung mass", "span": [258, 295], "codes": {"CPT": "32405"}},
        "prior_treatment": {"value": "None reported", "unit": None, "state": "absent", "evidence": "No prior treatment mentioned", "span": None, "codes": {}},
        "tumor_multiplicity": {"value": "Single primary; multiple brain metastases", "unit": None, "state": "present", "evidence": "single lung primary with multiple brain metastases", "span": [200, 245], "codes": {}}
    }
}

GOLD["report_004"] = {
    "report_id": "report_004",
    "cancer_type": "Breast",
    "procedure": "Ultrasound-guided core needle biopsy",
    "annotations": {
        "primary_site": {"value": "Right breast, upper inner quadrant", "unit": None, "state": "present", "evidence": "right breast mass... upper inner quadrant", "span": [86, 125], "codes": {"ICD-O-3": "C50.2"}},
        "histology_type": {"value": "Invasive ductal carcinoma, NST", "unit": None, "state": "present", "evidence": "invasive ductal carcinoma (IDC), NST, Nottingham Grade 3", "span": [412, 455], "codes": {"ICD-O-3-M": "8500/3"}},
        "tumor_grade": {"value": "Nottingham Grade 3", "unit": None, "state": "present", "evidence": "Nottingham Grade 3 (tubule score 3, nuclear score 3, mitotic score 3; total 9/9)", "span": [455, 528], "codes": {}},
        "clinical_stage": {"value": "Cannot be determined on biopsy", "unit": None, "state": "not_mentioned", "evidence": "Pathologic staging: cannot be determined on biopsy alone", "span": [790, 840], "codes": {}},
        "pathologic_stage": {"value": "Cannot be determined on biopsy", "unit": None, "state": "not_applicable", "evidence": "cannot be determined on biopsy alone", "span": [790, 840], "codes": {}},
        "tumor_size": {"value": "Not assessable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Imaging: mass described; biopsy cannot measure full tumor size", "span": None, "codes": {}},
        "laterality": {"value": "Right", "unit": None, "state": "present", "evidence": "right breast mass", "span": [86, 97], "codes": {}},
        "surgical_margins": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core needle biopsy", "span": None, "codes": {}},
        "lymph_nodes_examined": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy -- lymph nodes not sampled", "span": None, "codes": {}},
        "lymph_nodes_positive": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy -- lymph nodes not sampled", "span": None, "codes": {}},
        "lymphovascular_invasion": {"value": "Not assessable", "unit": None, "state": "not_applicable", "evidence": "Core biopsy -- LVI not assessable", "span": None, "codes": {}},
        "perineural_invasion": {"value": "Not assessable", "unit": None, "state": "not_applicable", "evidence": "Core biopsy -- PNI not assessable", "span": None, "codes": {}},
        "distant_metastasis": {"value": "Not mentioned", "unit": None, "state": "not_mentioned", "evidence": "No staging imaging or distant metastasis information in report", "span": None, "codes": {}},
        "er_status": {"value": "Equivocal / borderline (5%, 1+ intensity)", "unit": None, "state": "uncertain", "evidence": "ER -- equivocal result, 5% cells weakly positive (1+ intensity); borderline", "span": [555, 635], "codes": {}},
        "pr_status": {"value": "Negative (0%)", "unit": None, "state": "absent", "evidence": "PR: negative (0% cells)", "span": [636, 660], "codes": {}},
        "her2_status": {"value": "Positive (3+ IHC)", "unit": None, "state": "present", "evidence": "HER2: 3+ (positive by IHC)", "span": [661, 700], "codes": {}},
        "kras_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Breast cancer -- KRAS not applicable", "span": None, "codes": {}},
        "egfr_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Breast cancer -- EGFR not applicable", "span": None, "codes": {}},
        "procedure_type": {"value": "Ultrasound-guided core needle biopsy", "unit": None, "state": "present", "evidence": "Ultrasound-guided core needle biopsy performed", "span": [120, 160], "codes": {"CPT": "19083"}},
        "prior_treatment": {"value": "No prior breast procedures", "unit": None, "state": "absent", "evidence": "No prior breast procedures", "span": [115, 138], "codes": {}},
        "tumor_multiplicity": {"value": "Single lesion", "unit": None, "state": "absent", "evidence": "Single right breast mass described", "span": [86, 115], "codes": {}}
    }
}

GOLD["report_005"] = {
    "report_id": "report_005",
    "cancer_type": "Colorectal",
    "procedure": "Endoscopic mucosal resection biopsy",
    "annotations": {
        "primary_site": {"value": "Rectum, 10 cm from anal verge", "unit": None, "state": "present", "evidence": "sessile polyp in the rectum at 10 cm from the anal verge", "span": [115, 165], "codes": {"ICD-O-3": "C20.9"}},
        "histology_type": {"value": "Adenocarcinoma", "unit": None, "state": "present", "evidence": "well-differentiated (Grade 1) adenocarcinoma of the rectum", "span": [368, 415], "codes": {"ICD-O-3-M": "8140/3"}},
        "tumor_grade": {"value": "Grade 1 (well-differentiated)", "unit": None, "state": "present", "evidence": "well-differentiated (Grade 1)", "span": [368, 398], "codes": {}},
        "clinical_stage": {"value": "No distant metastasis on CT (pre-biopsy)", "unit": None, "state": "not_mentioned", "evidence": "CT: no evidence of distant metastatic disease", "span": [163, 225], "codes": {}},
        "pathologic_stage": {"value": "pT1 Nx (biopsy; full staging after resection)", "unit": None, "state": "uncertain", "evidence": "Stage: pT1 Nx (biopsy; full staging after definitive resection)", "span": [645, 700], "codes": {}},
        "tumor_size": {"value": "2.8", "unit": "cm", "state": "present", "evidence": "2.8 cm sessile polyp", "span": [100, 120], "codes": {}},
        "laterality": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Rectum -- laterality not applicable", "span": None, "codes": {}},
        "surgical_margins": {"value": "Appears uninvolved (limited assessment)", "unit": None, "state": "uncertain", "evidence": "deep biopsy margin appears uninvolved, though assessment is limited by fragmented nature", "span": [480, 560], "codes": {}},
        "lymph_nodes_examined": {"value": "Not assessed (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Lymph nodes: not assessed (biopsy specimen)", "span": [636, 670], "codes": {}},
        "lymph_nodes_positive": {"value": "Not assessed (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Lymph nodes: not assessed (biopsy specimen)", "span": [636, 670], "codes": {}},
        "lymphovascular_invasion": {"value": "Absent", "unit": None, "state": "absent", "evidence": "No lymphovascular invasion is identified", "span": [415, 455], "codes": {}},
        "perineural_invasion": {"value": "Absent", "unit": None, "state": "absent", "evidence": "Perineural invasion is absent", "span": [456, 482], "codes": {}},
        "distant_metastasis": {"value": "No evidence (CT and specimen)", "unit": None, "state": "absent", "evidence": "No evidence of metastasis in this specimen; CT: no distant disease", "span": [562, 625], "codes": {}},
        "er_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- ER not applicable", "span": None, "codes": {}},
        "pr_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- PR not applicable", "span": None, "codes": {}},
        "her2_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- HER2 not applicable", "span": None, "codes": {}},
        "kras_mutation": {"value": "Wild-type", "unit": None, "state": "absent", "evidence": "KRAS codon 12/13: wild-type", "span": [628, 655], "codes": {}},
        "egfr_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- EGFR not routinely tested", "span": None, "codes": {}},
        "procedure_type": {"value": "Endoscopic mucosal resection biopsy", "unit": None, "state": "present", "evidence": "Referred for endoscopic mucosal resection biopsy", "span": [226, 268], "codes": {"CPT": "45171"}},
        "prior_treatment": {"value": "None reported", "unit": None, "state": "absent", "evidence": "No prior treatment mentioned", "span": None, "codes": {}},
        "tumor_multiplicity": {"value": "Single lesion", "unit": None, "state": "absent", "evidence": "single 2.8 cm sessile polyp described", "span": [100, 165], "codes": {}}
    }
}

GOLD["report_006"] = {
    "report_id": "report_006",
    "cancer_type": "Lung",
    "procedure": "Left upper lobectomy",
    "annotations": {
        "primary_site": {"value": "Left upper lobe, lung", "unit": None, "state": "present", "evidence": "left upper lobe mass on CT (3.5 cm)", "span": [72, 100], "codes": {"ICD-O-3": "C34.1"}},
        "histology_type": {"value": "Squamous cell carcinoma", "unit": None, "state": "present", "evidence": "Poorly differentiated squamous cell carcinoma (SCC)", "span": [510, 560], "codes": {"ICD-O-3-M": "8070/3"}},
        "tumor_grade": {"value": "Grade 3 (poorly differentiated)", "unit": None, "state": "present", "evidence": "Poorly differentiated squamous cell carcinoma, Nottingham equivalent Grade 3", "span": [510, 575], "codes": {}},
        "clinical_stage": {"value": "Not assigned pre-operatively", "unit": None, "state": "not_mentioned", "evidence": "PET scan: both lesions FDG-avid; no mediastinal adenopathy; no distant metastases", "span": [155, 215], "codes": {}},
        "pathologic_stage": {"value": "pT3 pN0 pM0 -- Stage IIB", "unit": None, "state": "present", "evidence": "Pathologic stage: pT3 pN0 pM0 (satellite nodule) -- Stage IIB", "span": [1080, 1140], "codes": {"AJCC": "Stage IIB"}},
        "tumor_size": {"value": "3.5", "unit": "cm", "state": "present", "evidence": "firm, grey-white tumor measuring 3.5 x 3.2 x 3.0 cm", "span": [380, 425], "codes": {}},
        "laterality": {"value": "Left", "unit": None, "state": "present", "evidence": "Left upper lobectomy specimen", "span": [330, 360], "codes": {}},
        "surgical_margins": {"value": "Negative (bronchial margin 3.5 cm)", "unit": "cm", "state": "present", "evidence": "Bronchial resection margin: negative (3.5 cm from tumor)", "span": [620, 668], "codes": {}},
        "lymph_nodes_examined": {"value": "12", "unit": None, "state": "present", "evidence": "12 hilar and interlobar lymph nodes examined", "span": [700, 745], "codes": {}},
        "lymph_nodes_positive": {"value": "0", "unit": None, "state": "absent", "evidence": "no metastatic carcinoma identified (0/12)", "span": [746, 785], "codes": {}},
        "lymphovascular_invasion": {"value": "Absent", "unit": None, "state": "absent", "evidence": "No lymphovascular invasion identified", "span": [580, 615], "codes": {}},
        "perineural_invasion": {"value": "Absent", "unit": None, "state": "absent", "evidence": "Perineural invasion: absent", "span": [617, 642], "codes": {}},
        "distant_metastasis": {"value": "No evidence", "unit": None, "state": "absent", "evidence": "No evidence of distant metastasis; PET: no distant lesions", "span": [195, 220], "codes": {}},
        "er_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Squamous cell carcinoma -- ER not applicable", "span": None, "codes": {}},
        "pr_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Squamous cell carcinoma -- PR not applicable", "span": None, "codes": {}},
        "her2_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Squamous cell carcinoma -- HER2 not applicable", "span": None, "codes": {}},
        "kras_mutation": {"value": "Not tested (squamous, guideline-based)", "unit": None, "state": "not_mentioned", "evidence": "EGFR, KRAS, ALK: not tested (squamous histology, guideline-based)", "span": [800, 855], "codes": {}},
        "egfr_mutation": {"value": "Not tested (squamous, guideline-based)", "unit": None, "state": "not_mentioned", "evidence": "EGFR, KRAS, ALK: not tested (squamous histology, guideline-based)", "span": [800, 855], "codes": {}},
        "procedure_type": {"value": "Left upper lobectomy", "unit": None, "state": "present", "evidence": "Left upper lobectomy specimen", "span": [330, 355], "codes": {"CPT": "32480"}},
        "prior_treatment": {"value": "None reported", "unit": None, "state": "absent", "evidence": "No prior treatment mentioned", "span": None, "codes": {}},
        "tumor_multiplicity": {"value": "Multiple (primary + satellite nodule in lingula)", "unit": None, "state": "present", "evidence": "second distinct nodule measuring 12 x 10 x 9 mm in the lingula -- satellite nodule", "span": [450, 520], "codes": {}}
    }
}

GOLD["report_007"] = {
    "report_id": "report_007",
    "cancer_type": "Breast",
    "procedure": "Right mastectomy (post-neoadjuvant)",
    "annotations": {
        "primary_site": {"value": "Right breast, upper outer quadrant", "unit": None, "state": "present", "evidence": "right breast invasive ductal carcinoma... upper outer quadrant", "span": [72, 145], "codes": {"ICD-O-3": "C50.4"}},
        "histology_type": {"value": "Invasive ductal carcinoma, NST (residual, post-treatment)", "unit": None, "state": "present", "evidence": "residual invasive carcinoma with treatment effect (ypT1a)", "span": [618, 670], "codes": {"ICD-O-3-M": "8500/3"}},
        "tumor_grade": {"value": "Not re-gradable (treatment effect present)", "unit": None, "state": "uncertain", "evidence": "residual invasive carcinoma with treatment effect -- grade not assignable post-treatment", "span": None, "codes": {}},
        "clinical_stage": {"value": "Not provided (post-neoadjuvant context)", "unit": None, "state": "not_mentioned", "evidence": "No clinical TNM staging mentioned in report", "span": None, "codes": {}},
        "pathologic_stage": {"value": "ypT1a ypN0 ypM0", "unit": None, "state": "present", "evidence": "Post-treatment pathologic stage: ypT1a ypN0 ypM0", "span": [1000, 1040], "codes": {}},
        "tumor_size": {"value": "1", "unit": "mm", "state": "present", "evidence": "residual focus approximately 1 mm", "span": [660, 688], "codes": {}},
        "laterality": {"value": "Right", "unit": None, "state": "present", "evidence": "Right mastectomy", "span": [238, 255], "codes": {}},
        "surgical_margins": {"value": "Negative (closest margin >3 cm)", "unit": "cm", "state": "present", "evidence": "All surgical margins are negative (closest margin >3 cm)", "span": [690, 735], "codes": {}},
        "lymph_nodes_examined": {"value": "3 (sentinel)", "unit": None, "state": "present", "evidence": "Sentinel lymph nodes (3/3): no metastatic carcinoma", "span": [760, 805], "codes": {}},
        "lymph_nodes_positive": {"value": "0", "unit": None, "state": "absent", "evidence": "0/3 sentinel lymph nodes positive (ypN0)", "span": [760, 810], "codes": {}},
        "lymphovascular_invasion": {"value": "Absent (current specimen)", "unit": None, "state": "absent", "evidence": "No lymphovascular invasion in current specimen", "span": [738, 775], "codes": {}},
        "perineural_invasion": {"value": "Not mentioned", "unit": None, "state": "not_mentioned", "evidence": "PNI not mentioned in current report", "span": None, "codes": {}},
        "distant_metastasis": {"value": "Not mentioned", "unit": None, "state": "not_mentioned", "evidence": "No distant metastasis information provided", "span": None, "codes": {}},
        "er_status": {"value": "Positive (Allred 7/8, 80%, 3+)", "unit": None, "state": "present", "evidence": "ER positive (Allred 7/8, 80%, 3+ intensity)", "span": [840, 890], "codes": {}},
        "pr_status": {"value": "Positive (Allred 5/8, 30%, 2+)", "unit": None, "state": "present", "evidence": "PR positive (Allred 5/8, 30%, 2+ intensity)", "span": [891, 940], "codes": {}},
        "her2_status": {"value": "Negative (1+ IHC)", "unit": None, "state": "absent", "evidence": "HER2: 1+ (negative)", "span": [941, 960], "codes": {}},
        "kras_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Breast cancer -- KRAS not applicable", "span": None, "codes": {}},
        "egfr_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Breast cancer -- EGFR not applicable", "span": None, "codes": {}},
        "procedure_type": {"value": "Right mastectomy with sentinel lymph node biopsy", "unit": None, "state": "present", "evidence": "Referred for right mastectomy with sentinel lymph node biopsy", "span": [195, 248], "codes": {"CPT": "19303"}},
        "prior_treatment": {"value": "Neoadjuvant chemotherapy (AC-T, 6 cycles) + endocrine therapy", "unit": None, "state": "present", "evidence": "received neoadjuvant chemotherapy (AC-T regimen, 6 cycles) and endocrine therapy", "span": [148, 215], "codes": {}},
        "tumor_multiplicity": {"value": "Single lesion (residual)", "unit": None, "state": "absent", "evidence": "single residual focus at clip site", "span": [618, 660], "codes": {}}
    }
}

GOLD["report_008"] = {
    "report_id": "report_008",
    "cancer_type": "Colorectal",
    "procedure": "Right hemicolectomy",
    "annotations": {
        "primary_site": {"value": "Cecum", "unit": None, "state": "present", "evidence": "cecal mass... tumor identified at the cecum", "span": [85, 120], "codes": {"ICD-O-3": "C18.0"}},
        "histology_type": {"value": "Colorectal adenocarcinoma", "unit": None, "state": "present", "evidence": "moderately to poorly differentiated (Grade 2-3, mixed) colorectal adenocarcinoma", "span": [420, 490], "codes": {"ICD-O-3-M": "8140/3"}},
        "tumor_grade": {"value": "Grade 2-3 (mixed, moderately to poorly differentiated)", "unit": None, "state": "ambiguous", "evidence": "moderately to poorly differentiated (Grade 2-3, mixed)", "span": [420, 468], "codes": {}},
        "clinical_stage": {"value": "Not fully staged (no pre-op chest CT)", "unit": None, "state": "uncertain", "evidence": "no pre-operative staging CT of chest available", "span": [155, 195], "codes": {}},
        "pathologic_stage": {"value": "pT3 pN2a pMx -- Stage IIIC (provisional)", "unit": None, "state": "uncertain", "evidence": "pT3 pN2a pMx -- Stage IIIC (provisional; molecular pending)", "span": [870, 930], "codes": {}},
        "tumor_size": {"value": "5.5", "unit": "cm", "state": "present", "evidence": "fungating, partially obstructing tumor measuring 5.5 x 4.8 x 2.1 cm", "span": [326, 375], "codes": {}},
        "laterality": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Cecum -- laterality not applicable for colon", "span": None, "codes": {}},
        "surgical_margins": {"value": "CRM positive (tumor at inked margin <1 mm)", "unit": "mm", "state": "present", "evidence": "CRM: involved (tumor at inked surface, <1 mm)", "span": [625, 670], "codes": {}},
        "lymph_nodes_examined": {"value": "12", "unit": None, "state": "present", "evidence": "Of 12 lymph nodes examined", "span": [672, 696], "codes": {}},
        "lymph_nodes_positive": {"value": "5", "unit": None, "state": "present", "evidence": "5 are positive for metastatic adenocarcinoma with extranodal extension", "span": [697, 755], "codes": {}},
        "lymphovascular_invasion": {"value": "Indeterminate (suspicious but not confirmed)", "unit": None, "state": "uncertain", "evidence": "endothelial-lined spaces adjacent to tumor are suspicious", "span": [550, 615], "codes": {}},
        "perineural_invasion": {"value": "Absent", "unit": None, "state": "absent", "evidence": "Perineural invasion: absent", "span": [617, 642], "codes": {}},
        "distant_metastasis": {"value": "Not assessed (pMx)", "unit": None, "state": "uncertain", "evidence": "Distant metastasis: not assessed (no pre-op chest CT; tissue-based M stage unknown)", "span": [756, 820], "codes": {}},
        "er_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- ER not applicable", "span": None, "codes": {}},
        "pr_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- PR not applicable", "span": None, "codes": {}},
        "her2_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- HER2 not applicable", "span": None, "codes": {}},
        "kras_mutation": {"value": "Pending", "unit": None, "state": "uncertain", "evidence": "KRAS, NRAS, BRAF, MMR status: pending", "span": [822, 860], "codes": {}},
        "egfr_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Colorectal cancer -- EGFR not routinely tested", "span": None, "codes": {}},
        "procedure_type": {"value": "Right hemicolectomy", "unit": None, "state": "present", "evidence": "Referred urgently for right hemicolectomy", "span": [195, 220], "codes": {"CPT": "44160"}},
        "prior_treatment": {"value": "None reported", "unit": None, "state": "absent", "evidence": "No prior treatment mentioned", "span": None, "codes": {}},
        "tumor_multiplicity": {"value": "Single lesion", "unit": None, "state": "absent", "evidence": "single fungating mass at cecum", "span": [326, 390], "codes": {}}
    }
}

GOLD["report_009"] = {
    "report_id": "report_009",
    "cancer_type": "Lung",
    "procedure": "CT-guided core needle biopsy",
    "annotations": {
        "primary_site": {"value": "Right lower lobe, lung (suspected)", "unit": None, "state": "uncertain", "evidence": "right lower lobe nodule (1.8 cm)... suspicious for malignancy", "span": [95, 135], "codes": {"ICD-O-3": "C34.3"}},
        "histology_type": {"value": "Suspicious for adenocarcinoma (not confirmed)", "unit": None, "state": "uncertain", "evidence": "suspicious for adenocarcinoma, but definitive malignant criteria are not fully met", "span": [420, 495], "codes": {}},
        "tumor_grade": {"value": "Cannot be determined", "unit": None, "state": "not_mentioned", "evidence": "Grade not assigned -- diagnosis not confirmed", "span": None, "codes": {}},
        "clinical_stage": {"value": "Cannot be determined", "unit": None, "state": "not_mentioned", "evidence": "Stage: cannot be determined", "span": [750, 775], "codes": {}},
        "pathologic_stage": {"value": "Cannot be determined", "unit": None, "state": "not_applicable", "evidence": "Stage: cannot be determined (suspicious, not confirmed)", "span": None, "codes": {}},
        "tumor_size": {"value": "1.8", "unit": "cm", "state": "present", "evidence": "right lower lobe nodule (1.8 cm)", "span": [95, 115], "codes": {}},
        "laterality": {"value": "Right", "unit": None, "state": "present", "evidence": "right lower lobe", "span": [95, 112], "codes": {}},
        "surgical_margins": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "lymph_nodes_examined": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "lymph_nodes_positive": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "lymphovascular_invasion": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "perineural_invasion": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "distant_metastasis": {"value": "Not mentioned", "unit": None, "state": "not_mentioned", "evidence": "No staging imaging results in this report", "span": None, "codes": {}},
        "er_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Lung (suspected) -- ER not applicable", "span": None, "codes": {}},
        "pr_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Lung (suspected) -- PR not applicable", "span": None, "codes": {}},
        "her2_status": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Lung (suspected) -- HER2 not applicable", "span": None, "codes": {}},
        "kras_mutation": {"value": "Not tested", "unit": None, "state": "not_mentioned", "evidence": "KRAS: not tested", "span": [680, 700], "codes": {}},
        "egfr_mutation": {"value": "Pending (insufficient tissue)", "unit": None, "state": "uncertain", "evidence": "EGFR mutation analysis: pending (insufficient tissue extracted for reliable result)", "span": [645, 712], "codes": {}},
        "procedure_type": {"value": "CT-guided core needle biopsy", "unit": None, "state": "present", "evidence": "Referred for CT-guided core biopsy", "span": [218, 248], "codes": {"CPT": "32405"}},
        "prior_treatment": {"value": "Prior left lobectomy (squamous cell carcinoma, 3 years ago)", "unit": None, "state": "present", "evidence": "prior left lobectomy for squamous cell carcinoma 3 years ago", "span": [115, 175], "codes": {}},
        "tumor_multiplicity": {"value": "Single new nodule (historical left-sided SCC separate)", "unit": None, "state": "uncertain", "evidence": "single right lower lobe nodule; history of left-sided SCC", "span": [95, 180], "codes": {}}
    }
}

GOLD["report_010"] = {
    "report_id": "report_010",
    "cancer_type": "Breast",
    "procedure": "Stereotactic core biopsy (two specimens)",
    "annotations": {
        "primary_site": {"value": "Left breast (upper outer and lower outer quadrants)", "unit": None, "state": "present", "evidence": "two distinct suspicious lesions... upper outer quadrant; lower outer quadrant", "span": [120, 220], "codes": {"ICD-O-3": "C50.4"}},
        "histology_type": {"value": "Specimen A: IDC NST + DCIS; Specimen B: DCIS only", "unit": None, "state": "present", "evidence": "Specimen A: invasive ductal carcinoma + high-grade DCIS; Specimen B: high-grade DCIS only", "span": [430, 620], "codes": {"ICD-O-3-M": "8500/3 (IDC); 8500/2 (DCIS)"}},
        "tumor_grade": {"value": "Specimen A: Grade 3 (Nottingham 8/9); Specimen B: high-grade DCIS", "unit": None, "state": "present", "evidence": "Nottingham Grade 3 (score 8/9); high-grade DCIS", "span": [460, 510], "codes": {}},
        "clinical_stage": {"value": "Not applicable on biopsy", "unit": None, "state": "not_applicable", "evidence": "Full staging: not applicable on core biopsy", "span": [870, 910], "codes": {}},
        "pathologic_stage": {"value": "Not applicable on biopsy", "unit": None, "state": "not_applicable", "evidence": "Full staging: not applicable on core biopsy", "span": None, "codes": {}},
        "tumor_size": {"value": "Specimen A: 18 mm; Specimen B: 9 mm (imaging)", "unit": "mm", "state": "present", "evidence": "Lesion A -- 18 mm mass; Lesion B -- 9 mm mass", "span": [150, 195], "codes": {}},
        "laterality": {"value": "Left", "unit": None, "state": "present", "evidence": "left breast microcalcifications", "span": [72, 90], "codes": {}},
        "surgical_margins": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "lymph_nodes_examined": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "lymph_nodes_positive": {"value": "Not applicable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "lymphovascular_invasion": {"value": "Not assessable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "perineural_invasion": {"value": "Not assessable (biopsy)", "unit": None, "state": "not_applicable", "evidence": "Core biopsy", "span": None, "codes": {}},
        "distant_metastasis": {"value": "Not mentioned", "unit": None, "state": "not_mentioned", "evidence": "No staging imaging described", "span": None, "codes": {}},
        "er_status": {"value": "Specimen A: Positive (Allred 7/8, 70%); Specimen B: Positive (Allred 6/8, 50%)", "unit": None, "state": "present", "evidence": "ER positive (Allred 7/8, 70%, 3+); ER positive (Allred 6/8, 50%, 2+)", "span": [520, 620], "codes": {}},
        "pr_status": {"value": "Specimen A: Equivocal (10%, 1+); Specimen B: Positive (Allred 5/8, 30%)", "unit": None, "state": "ambiguous", "evidence": "PR: equivocal (10%, 1+); PR positive (Allred 5/8, 30%, 2+)", "span": [621, 700], "codes": {}},
        "her2_status": {"value": "Specimen A: Equivocal (2+ IHC, FISH recommended); Specimen B: Negative (1+)", "unit": None, "state": "uncertain", "evidence": "HER2: 2+ (equivocal by IHC); FISH recommended; HER2: 1+ (negative)", "span": [701, 780], "codes": {}},
        "kras_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Breast cancer -- KRAS not applicable", "span": None, "codes": {}},
        "egfr_mutation": {"value": "Not applicable", "unit": None, "state": "not_applicable", "evidence": "Breast cancer -- EGFR not applicable", "span": None, "codes": {}},
        "procedure_type": {"value": "Stereotactic core biopsy (two separate specimens)", "unit": None, "state": "present", "evidence": "Stereotactic core biopsy performed of both lesions separately", "span": [230, 270], "codes": {"CPT": "19081"}},
        "prior_treatment": {"value": "None reported", "unit": None, "state": "absent", "evidence": "No prior treatment mentioned", "span": None, "codes": {}},
        "tumor_multiplicity": {"value": "Multifocal (two lesions, 4 cm apart)", "unit": None, "state": "present", "evidence": "Synchronous multifocal disease: present (two lesions, 4 cm apart)", "span": [845, 900], "codes": {}}
    }
}
