import sys
import os
import json
from pathlib import Path

# Add common to path
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "common"))

from schema import empty_output, PIPELINE_A

import sparknlp
from sparknlp.base import *
from sparknlp.annotator import *
from sparknlp_jsl.annotator import *
from sparknlp_jsl.pretrained import *
import sparknlp_jsl

# Start Spark
spark = sparknlp_jsl.start(secret='5.4.0-0e2bf7e015ecf5ffc656c250cd1a03605ade4312', gpu=False)

print("Building pipeline...")

document_assembler = DocumentAssembler()\
    .setInputCol("text")\
    .setOutputCol("document")

sentence_detector = SentenceDetectorDLModel.pretrained("sentence_detector_dl_healthcare", "en", "clinical/models")\
    .setInputCols(["document"])\
    .setOutputCol("sentence")

tokenizer = Tokenizer()\
    .setInputCols(["sentence"])\
    .setOutputCol("token")

word_embeddings = WordEmbeddingsModel.pretrained("embeddings_clinical", "en", "clinical/models")\
    .setInputCols(["sentence", "token"])\
    .setOutputCol("embeddings")

# NER 1
ner_oncology = MedicalNerModel.pretrained("ner_oncology_wip", "en", "clinical/models")\
    .setInputCols(["sentence", "token", "embeddings"])\
    .setOutputCol("ner_onc")
ner_converter_onc = NerConverterInternal()\
    .setInputCols(["sentence", "token", "ner_onc"])\
    .setOutputCol("ner_chunk_onc")

# NER 2
ner_biomarker = MedicalNerModel.pretrained("ner_oncology_biomarker_wip", "en", "clinical/models")\
    .setInputCols(["sentence", "token", "embeddings"])\
    .setOutputCol("ner_bio")
ner_converter_bio = NerConverterInternal()\
    .setInputCols(["sentence", "token", "ner_bio"])\
    .setOutputCol("ner_chunk_bio")

# NER 3
ner_tnm = MedicalNerModel.pretrained("ner_oncology_tnm_wip", "en", "clinical/models")\
    .setInputCols(["sentence", "token", "embeddings"])\
    .setOutputCol("ner_tnm")
ner_converter_tnm = NerConverterInternal()\
    .setInputCols(["sentence", "token", "ner_tnm"])\
    .setOutputCol("ner_chunk_tnm")

# Merge
chunk_merge = ChunkMergeApproach()\
    .setInputCols(["ner_chunk_onc", "ner_chunk_bio", "ner_chunk_tnm"])\
    .setOutputCol("merged_chunk")

# Assertion
assertion = AssertionDLModel.pretrained("assertion_oncology_wip", "en", "clinical/models")\
    .setInputCols(["sentence", "merged_chunk", "embeddings"])\
    .setOutputCol("assertion")

# Relation Extraction requires POS and Dependency
pos_tagger = PerceptronModel.pretrained("pos_clinical", "en", "clinical/models")\
    .setInputCols(["sentence", "token"])\
    .setOutputCol("pos")
dependency_parser = DependencyParserModel.pretrained("dependency_conllu", "en")\
    .setInputCols(["sentence", "pos", "token"])\
    .setOutputCol("dependencies")

re_model = RelationExtractionModel.pretrained("re_oncology_wip", "en", "clinical/models")\
    .setInputCols(["embeddings", "pos", "merged_chunk", "dependencies"])\
    .setOutputCol("relations")\
    .setRelationPairs(["Biomarker-Biomarker_Result", "Tumor_Finding-Site", "Tumor_Finding-Size"])

# Resolvers require chunk embeddings
chunk2doc = Chunk2Doc()\
    .setInputCols(["merged_chunk"])\
    .setOutputCol("chunk_doc")

sbert = BertSentenceEmbeddings.pretrained("sbiobert_base_cased_mli", "en", "clinical/models")\
    .setInputCols(["chunk_doc"])\
    .setOutputCol("chunk_embeddings")

resolver_icd10 = SentenceEntityResolverModel.pretrained("sbiobertresolve_icd10cm_augmented_billable", "en", "clinical/models")\
    .setInputCols(["chunk_embeddings"])\
    .setOutputCol("icd10_code")\
    .setDistanceFunction("EUCLIDEAN")

resolver_icdo = SentenceEntityResolverModel.pretrained("sbiobertresolve_icdo", "en", "clinical/models")\
    .setInputCols(["chunk_embeddings"])\
    .setOutputCol("icdo_code")\
    .setDistanceFunction("EUCLIDEAN")

pipeline = Pipeline(stages=[
    document_assembler,
    sentence_detector,
    tokenizer,
    word_embeddings,
    ner_oncology, ner_converter_onc,
    ner_biomarker, ner_converter_bio,
    ner_tnm, ner_converter_tnm,
    chunk_merge,
    assertion,
    pos_tagger, dependency_parser, re_model,
    chunk2doc, sbert, resolver_icd10, resolver_icdo
])

with open("data/raw/report_001.txt", "r", encoding="utf-8") as f:
    text = f.read()

print("Fitting pipeline...")
model = pipeline.fit(spark.createDataFrame([[""]]).toDF("text"))

from sparknlp.base import LightPipeline
lp = LightPipeline(model)

print("Annotating...")
res = lp.fullAnnotate(text)[0]

print("Done. Printing chunks:")
for c, a in zip(res.get("merged_chunk", []), res.get("assertion", [])):
    print(f"{c.result} [{c.metadata['entity']}] -> {a.result}")
