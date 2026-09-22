#!/usr/bin/env bash
# =============================================================================
# run_all.sh
# =============================================================================
# Orchestrates the full Oncology Registry Extraction pipeline end-to-end:
#
#   Step 1  Build terminology FAISS index (Pipeline B prerequisite)
#   Step 2  Run Pipeline A  — Classical Healthcare NLP (JSL / heuristic)
#   Step 3  Run Pipeline B  — LLM + Local Terminology Retrieval
#   Step 4  Validate both pipeline outputs against the shared JSON schema
#   Step 5  Compute field-level agreement against gold annotations
#
# Usage:
#   bash run_all.sh                       # full run
#   bash run_all.sh --skip-pipeline-a     # run only Pipeline B + validation
#   bash run_all.sh --skip-pipeline-b     # run only Pipeline A + validation
#   bash run_all.sh --report report_001   # process a single report through both pipelines
#
# Environment variables (optional):
#   JSL_LICENSE_PATH   — path to John Snow Labs license JSON (enables licensed JSL NER)
#   OPENAI_API_KEY     — OpenAI API key (enables LLM extraction in Pipeline B)
#   LLM_API_BASE       — base URL for OpenAI-compatible local LLM (e.g. Ollama)
#   LLM_MODEL          — model name (default: gpt-4o-mini)
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colour output helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'   # No colour

log_info()  { echo -e "${BLUE}[INFO ]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK   ]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN ]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step()  { echo -e "\n${BOLD}${BLUE}==== $* ====${NC}"; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
SKIP_A=0
SKIP_B=0
SINGLE_REPORT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-pipeline-a) SKIP_A=1; shift ;;
        --skip-pipeline-b) SKIP_B=1; shift ;;
        --report)          SINGLE_REPORT="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: bash run_all.sh [--skip-pipeline-a] [--skip-pipeline-b] [--report report_XXX]"
            exit 0
            ;;
        *) log_error "Unknown argument: $1"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
INPUT_DIR="$PROJECT_ROOT/data/raw"
GOLD_DIR="$PROJECT_ROOT/data/gold"
OUTPUT_A="$PROJECT_ROOT/outputs/pipeline_a"
OUTPUT_B="$PROJECT_ROOT/outputs/pipeline_b"

REPORT_FLAG=""
if [[ -n "$SINGLE_REPORT" ]]; then
    REPORT_FLAG="--report-id $SINGLE_REPORT"
fi

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   Oncology Registry Extraction  —  run_all.sh          ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Project root  : $PROJECT_ROOT"
log_info "Timestamp     : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
log_info "Input dir     : $INPUT_DIR"
log_info "Pipeline A out: $OUTPUT_A"
log_info "Pipeline B out: $OUTPUT_B"
[[ -n "$JSL_LICENSE_PATH"  ]] && log_info "JSL license   : $JSL_LICENSE_PATH" || log_warn "JSL_LICENSE_PATH not set — Pipeline A will use heuristic mode"
[[ -n "${OPENAI_API_KEY:-}"   ]] && log_info "OpenAI key    : ****" || log_warn "OPENAI_API_KEY not set — Pipeline B will use deterministic mode"
[[ -n "${LLM_API_BASE:-}"     ]] && log_info "LLM API base  : $LLM_API_BASE"

mkdir -p "$OUTPUT_A" "$OUTPUT_B"

# ---------------------------------------------------------------------------
# Step 1: Build terminology FAISS index
# ---------------------------------------------------------------------------
log_step "Step 1/4  Build Terminology FAISS Index"
python src/pipeline_b_llm_retrieval/terminology_index.py --build
log_ok "FAISS index built"

# ---------------------------------------------------------------------------
# Step 2: Pipeline A — Classical NLP
# ---------------------------------------------------------------------------
if [[ $SKIP_A -eq 0 ]]; then
    log_step "Step 2/4  Pipeline A  —  Classical Healthcare NLP (JSL)"
    python src/pipeline_a_classical/run.py \
        --input  "$INPUT_DIR" \
        --output "$OUTPUT_A" \
        $REPORT_FLAG
    log_ok "Pipeline A complete → $OUTPUT_A"
else
    log_warn "Skipping Pipeline A (--skip-pipeline-a)"
fi

# ---------------------------------------------------------------------------
# Step 3: Pipeline B — LLM + Retrieval
# ---------------------------------------------------------------------------
if [[ $SKIP_B -eq 0 ]]; then
    log_step "Step 3/4  Pipeline B  —  LLM + Local Terminology Retrieval"
    python src/pipeline_b_llm_retrieval/run.py \
        --input  "$INPUT_DIR" \
        --output "$OUTPUT_B" \
        $REPORT_FLAG
    log_ok "Pipeline B complete → $OUTPUT_B"
else
    log_warn "Skipping Pipeline B (--skip-pipeline-b)"
fi

# ---------------------------------------------------------------------------
# Step 4: Validate + Agreement
# ---------------------------------------------------------------------------
log_step "Step 4/4  Validation and Agreement Scoring"
python src/common/validate.py \
    $( [[ $SKIP_A -eq 0 ]] && echo "--pipeline-a $OUTPUT_A" || true ) \
    $( [[ $SKIP_B -eq 0 ]] && echo "--pipeline-b $OUTPUT_B" || true ) \
    $( [[ -d "$GOLD_DIR" ]] && echo "--gold $GOLD_DIR" || true )

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║   run_all.sh  COMPLETE                                 ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
