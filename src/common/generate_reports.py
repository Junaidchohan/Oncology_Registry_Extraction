"""
generate_reports.py
===================
Deterministically generates 10 synthetic oncology pathology reports and their
corresponding gold-standard annotations for the Oncology Registry Extraction project.

21 annotation fields (per assessment schema):
  1.  primary_site            12. perineural_invasion
  2.  histology_type          13. distant_metastasis
  3.  tumor_grade             14. er_status
  4.  clinical_stage          15. pr_status
  5.  pathologic_stage        16. her2_status
  6.  tumor_size              17. kras_mutation
  7.  laterality              18. egfr_mutation
  8.  surgical_margins        19. procedure_type
  9.  lymph_nodes_examined    20. prior_treatment
  10. lymph_nodes_positive    21. tumor_multiplicity
  11. lymphovascular_invasion

State vocabulary:
  present | absent | uncertain | not_mentioned | not_applicable | ambiguous

Reports cover:
  - Breast, Colorectal, and Lung cancers
  - Biopsies and surgical resections
  - Negated findings, uncertain/suspicious findings, multiple lesions
  - Historical vs current disease
  - Biomarkers: ER, PR, HER2, KRAS, EGFR
  - Varied units (cm, mm)
  - Genuinely missing/pending information

Usage:
    python src/common/generate_reports.py [--base-dir PATH]

Default base directory is the project root (two levels up from this script).
"""

import argparse
import json
import os
import sys

# ---------------------------------------------------------------------------
# Import data from sibling modules in the same package directory
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from _report_data import REPORTS  # noqa: E402  (local import)
from _gold_data import GOLD        # noqa: E402  (local import)


# ---------------------------------------------------------------------------
# Core writer
# ---------------------------------------------------------------------------

def write_reports(base_dir: str = ".") -> None:
    """Write synthetic reports to data/raw/ and gold annotations to data/gold/."""
    raw_dir = os.path.join(base_dir, "data", "raw")
    gold_dir = os.path.join(base_dir, "data", "gold")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(gold_dir, exist_ok=True)

    # ---- raw reports -------------------------------------------------------
    for report_id in sorted(REPORTS):
        raw_path = os.path.join(raw_dir, f"{report_id}.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(REPORTS[report_id])
        print(f"[OK] Written report : {os.path.relpath(raw_path, base_dir)}")

    # ---- gold annotations --------------------------------------------------
    for report_id in sorted(GOLD):
        gold_path = os.path.join(gold_dir, f"{report_id}.json")
        with open(gold_path, "w", encoding="utf-8") as f:
            json.dump(GOLD[report_id], f, indent=2, ensure_ascii=False)
        print(f"[OK] Written gold   : {os.path.relpath(gold_path, base_dir)}")

    total_fields = sum(len(v["annotations"]) for v in GOLD.values())
    print(
        f"\nDone. {len(REPORTS)} reports | {len(GOLD)} gold files | "
        f"{total_fields} total annotated fields written to '{base_dir}'."
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _resolve_project_root() -> str:
    """Return absolute path to the project root (two directories above this file)."""
    return os.path.abspath(os.path.join(_HERE, "..", ".."))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate synthetic oncology reports and gold annotations."
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help=(
            "Project root directory. Defaults to the project root inferred "
            "from this script's location (../../ relative to src/common/)."
        ),
    )
    args = parser.parse_args()

    base_dir = args.base_dir if args.base_dir else _resolve_project_root()
    base_dir = os.path.abspath(base_dir)
    print(f"Project root: {base_dir}\n")
    write_reports(base_dir=base_dir)


if __name__ == "__main__":
    main()
