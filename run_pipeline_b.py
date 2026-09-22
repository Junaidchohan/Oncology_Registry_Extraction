import json, sys, logging, importlib.util
from pathlib import Path
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
sys.path.insert(0, 'src/common')
sys.path.insert(0, 'src/pipeline_a_classical')

# Load pipeline_b's pipeline.py explicitly to avoid name collision with pipeline_a's pipeline.py
_spec = importlib.util.spec_from_file_location(
    "pipeline_b", "src/pipeline_b_llm_retrieval/pipeline.py"
)
_pipeline_b = importlib.util.module_from_spec(_spec)
sys.modules["pipeline_b"] = _pipeline_b
_spec.loader.exec_module(_pipeline_b)
build_pipeline_b_components = _pipeline_b.build_pipeline_b_components
run_pipeline_b = _pipeline_b.run_pipeline_b

print('Building Pipeline B components...')
extractor, grounding_engine = build_pipeline_b_components()
print('Ready.')

input_dir = Path('data/raw')
output_dir = Path('outputs/pipeline_b')
output_dir.mkdir(parents=True, exist_ok=True)

for report_file in sorted(input_dir.glob('report_*.txt')):
    rid = report_file.stem
    text = report_file.read_text(encoding='utf-8')
    out = run_pipeline_b(rid, text, extractor, grounding_engine)
    out_path = output_dir / (rid + '.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
    non_empty = sum(1 for v in out['fields'].values() if v.get('value'))
    coded = sum(1 for v in out['fields'].values() if v.get('codes'))
    print(rid + ': ' + str(non_empty) + '/21 fields, ' + str(coded) + ' with grounded codes')

print('Pipeline B complete.')
