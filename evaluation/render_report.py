import json
from pathlib import Path

def inject(text, table):
    # Find markers and replace
    start = "<!-- BEGIN EVAL TABLE -->"
    end = "<!-- END EVAL TABLE -->"
    if start in text and end in text:
        before = text.split(start)[0]
        after = text.split(end)[1]
        return before + start + "\n\n" + table + "\n\n" + end + after
    return text

def run():
    root = Path(__file__).resolve().parents[1]
    table = (root / "evaluation" / "comparison_table.md").read_text(encoding="utf-8")
    
    for doc in ["README.md", "SUBMISSION.md", "report/report.md"]:
        p = root / doc
        if p.exists():
            t = p.read_text(encoding="utf-8")
            t_new = inject(t, table)
            p.write_text(t_new, encoding="utf-8")

if __name__ == "__main__":
    run()
