import logging, sys
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, 'src/pipeline_b_llm_retrieval')
from terminology_index import TerminologyIndex
idx = TerminologyIndex()
idx.build()
print('Backend used:', idx._backend)
results = idx.search('invasive ductal carcinoma', top_k=3)
for r in results:
    term = r['terminology']
    code = r['code']
    name = r['concept_name']
    score = r['score']
    print(f'  [{term}] {code:12s} {name} (score={score:.3f})')
print('SEARCH OK')
