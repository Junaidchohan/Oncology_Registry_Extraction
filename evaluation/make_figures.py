import json
import csv
import os
import glob
import re
import matplotlib.pyplot as plt
import numpy as np

# Ensure docs/figures exists
os.makedirs("docs/figures", exist_ok=True)

# FIGURE 1: Pipeline Comparison Bar Chart
def make_fig1():
    with open("evaluation/results.json", "r") as f:
        results = json.load(f)
    
    # metrics: NER F1, Field value exact accuracy, Retrieval Recall@K, Selection accuracy
    metrics = ["NER F1", "Field value exact accuracy", "Retrieval Recall@K", "Selection accuracy"]
    
    pa_f1 = results.get("pipeline_a", {}).get("overall", {}).get("entity", {}).get("f1", 0) * 100
    pa_field = results.get("pipeline_a", {}).get("overall", {}).get("field", {}).get("accuracy", 0) * 100
    pa_recall = results.get("pipeline_a", {}).get("overall", {}).get("terminology", {}).get("recall_at_k", 0) * 100
    pa_sel = results.get("pipeline_a", {}).get("overall", {}).get("terminology", {}).get("selection_accuracy", 0) * 100
    
    pb_f1 = results.get("pipeline_b", {}).get("overall", {}).get("entity", {}).get("f1", 0) * 100
    pb_field = results.get("pipeline_b", {}).get("overall", {}).get("field", {}).get("accuracy", 0) * 100
    pb_recall = results.get("pipeline_b", {}).get("overall", {}).get("terminology", {}).get("recall_at_k", 0) * 100
    pb_sel = results.get("pipeline_b", {}).get("overall", {}).get("terminology", {}).get("selection_accuracy", 0) * 100
    
    pa_vals = [pa_f1, pa_field, pa_recall, pa_sel]
    pb_vals = [pb_f1, pb_field, pb_recall, pb_sel]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    rects1 = ax.bar(x - width/2, pa_vals, width, label='Pipeline A')
    rects2 = ax.bar(x + width/2, pb_vals, width, label='Pipeline B')
    
    ax.set_ylabel('Percentage (%)')
    ax.set_title('Pipeline A vs Pipeline B — key metrics')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylim([0, 100])
    ax.legend(loc='upper right')
    
    ax.bar_label(rects1, fmt='%.1f%%', padding=3)
    ax.bar_label(rects2, fmt='%.1f%%', padding=3)
    
    fig.tight_layout()
    plt.savefig("docs/figures/01_pipeline_comparison.png", dpi=150)
    plt.close()

# FIGURE 2: Per-Field Accuracy Heatmap
def make_fig2():
    fields = []
    pa_accs = []
    pb_accs = []
    
    with open("evaluation/per_field_results.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fields.append(row["field"])
            # The CSV might just have Pipeline A / Pipeline B columns or we might have to parse
            # Let's check results.json for fields instead if CSV is harder to parse without knowing format.
            pass
            
    # Reading from results.json directly is safer since we know its structure from before.
    with open("evaluation/results.json", "r") as f:
        results = json.load(f)
        
    pa_fields = results.get("pipeline_a", {}).get("per_field", {})
    pb_fields = results.get("pipeline_b", {}).get("per_field", {})
    
    fields = sorted(list(set(pa_fields.keys()).union(set(pb_fields.keys()))))
    
    for f in fields:
        pa_accs.append(pa_fields.get(f, {}).get("field", {}).get("accuracy", 0) * 100)
        pb_accs.append(pb_fields.get(f, {}).get("field", {}).get("accuracy", 0) * 100)
        
    data = np.array([pa_accs, pb_accs]).T
    
    fig, ax = plt.subplots(figsize=(8, 10))
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)
    
    ax.set_yticks(np.arange(len(fields)))
    ax.set_yticklabels(fields)
    ax.set_xticks(np.arange(2))
    ax.set_xticklabels(["Pipeline A", "Pipeline B"])
    
    for i in range(len(fields)):
        for j in range(2):
            text = ax.text(j, i, f"{data[i, j]:.1f}%", ha="center", va="center", color="black" if 30 < data[i,j] < 70 else "white")
            
    ax.set_title("Per-field accuracy by pipeline")
    fig.tight_layout()
    plt.savefig("docs/figures/02_per_field_heatmap.png", dpi=150)
    plt.close()

# FIGURE 3: Error Distribution
def make_fig3():
    causes_map = {
        "extraction": 0,
        "context/assertion": 0,
        "wrong relationship": 0,
        "retrieval miss": 0,
        "incorrect concept selection": 0,
        "schema failure": 0,
        "unsupported inference": 0
    }
    
    if os.path.exists("report/report.md"):
        with open("report/report.md", "r") as f:
            content = f.read()
            for m in re.finditer(r"\*\*Root cause\*\*:\s*([^<]+)", content, re.IGNORECASE):
                val = m.group(1).strip().lower()
                matched = False
                for c in causes_map.keys():
                    if c in val:
                        causes_map[c] += 1
                        matched = True
                        break
                if not matched:
                    print(f"Unmatched root cause: {val}")
                    
    # Sorting
    sorted_causes = sorted(causes_map.items(), key=lambda x: x[1])
    labels = [x[0] for x in sorted_causes]
    vals = [x[1] for x in sorted_causes]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(labels, vals)
    ax.set_xlabel('Count')
    ax.set_title('Error distribution across eight documented discrepancies')
    ax.bar_label(bars)
    
    fig.tight_layout()
    plt.savefig("docs/figures/03_error_distribution.png", dpi=150)
    plt.close()

# FIGURE 4: State Accuracy Breakdown
def make_fig4():
    def get_state_counts(pipeline_dir):
        counts = {
            "present": 0,
            "negative": 0,
            "not_mentioned": 0,
            "not_assessed": 0,
            "not_applicable": 0,
            "ambiguous": 0
        }
        for f in glob.glob(os.path.join(pipeline_dir, "report_*.json")):
            with open(f, "r") as fp:
                data = json.load(fp)
                for ann in data.get("annotations", []):
                    # check top-level annotations
                    state = ann.get("state")
                    if state in counts:
                        counts[state] += 1
                    
                    # check biomarkers specifically as they are repeatable
                    if ann.get("field_name") == "biomarkers":
                        for b in ann.get("value", []):
                            s = b.get("state")
                            if s in counts:
                                counts[s] += 1
        return counts

    c_a = get_state_counts("outputs/pipeline_a")
    c_b = get_state_counts("outputs/pipeline_b")
    
    states = ["present", "negative", "not_mentioned", "not_assessed", "not_applicable", "ambiguous"]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bottom_a = 0
    bottom_b = 0
    
    for s in states:
        v_a = c_a[s]
        v_b = c_b[s]
        ax.bar("Pipeline A", v_a, bottom=bottom_a, label=s)
        ax.bar("Pipeline B", v_b, bottom=bottom_b)
        bottom_a += v_a
        bottom_b += v_b
        
    ax.set_ylabel('Count of fields')
    ax.set_title('State label distribution by pipeline')
    
    # Deduplicate legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper right', bbox_to_anchor=(1.25, 1))
    
    fig.tight_layout()
    plt.savefig("docs/figures/04_state_accuracy.png", dpi=150)
    plt.close()

# FIGURE 5: Runtime Comparison
def make_fig5():
    # Mean runtime per report for each pipeline:
    # Pipeline A: 32.85s
    # Pipeline B: 1354.28s
    
    with open("evaluation/results.json", "r") as f:
        results = json.load(f)
        pa_time = results.get("pipeline_a", {}).get("overall", {}).get("runtime", 32.85)
        pb_time = results.get("pipeline_b", {}).get("overall", {}).get("runtime", 1354.28)
        
    labels = ["Pipeline A", "Pipeline B"]
    vals = [pa_time, pb_time]
    
    fig, ax = plt.subplots(figsize=(6, 6))
    bars = ax.bar(labels, vals)
    ax.set_yscale('log')
    ax.set_ylabel('Time (s)')
    ax.set_title('Mean runtime per report (log scale)')
    
    ax.bar_label(bars, fmt='%.2fs')
    
    plt.figtext(0.5, 0.01, "Pipeline B's runtime reflects CPU-only inference. GPU would reduce this substantially.", ha="center", fontsize=10, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
    
    # Adjust layout to accommodate the text at the bottom
    plt.subplots_adjust(bottom=0.15)
    
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig("docs/figures/05_runtime_comparison.png", dpi=150)
    plt.close()

if __name__ == "__main__":
    make_fig1()
    make_fig2()
    make_fig3()
    make_fig4()
    make_fig5()
