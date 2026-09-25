import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src" / "pipeline_a_classical"))

import pipeline_jsl

data_dir = _ROOT / "data" / "raw"
output_dir = _ROOT / "outputs" / "pipeline_a"

pipeline_jsl.run_all(data_dir=data_dir, output_dir=output_dir)
