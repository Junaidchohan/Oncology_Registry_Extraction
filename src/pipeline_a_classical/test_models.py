from pipeline_jsl import start_spark
from sparknlp_jsl.annotator import SentenceEntityResolverModel

spark = start_spark()

models = [
    'sbiobertresolve_icd10cm_augmented_billable',
    'sbiobertresolve_icd10cm',
    'sbiobertresolve_icd10cm_augmented',
    'sbiobertresolve_icdo',
    'sbiobertresolve_icdo_base'
]

for m in models:
    try:
        print(f'Testing {m}...')
        resolver = SentenceEntityResolverModel.pretrained(m, 'en', 'clinical/models')
        print(f' SUCCESS: {m}')
    except Exception as e:
        print(f' FAILED: {m} - {e}')
