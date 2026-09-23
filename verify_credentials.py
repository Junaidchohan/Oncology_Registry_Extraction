"""
verify_credentials.py — Test OpenAI API key and JSL license validity
Run: python verify_credentials.py
"""
import sys, os, json
from pathlib import Path

# Load config
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'common'))
from config import OPENAI_API_KEY, LLM_MODEL, JSL_LICENSE_PATH

print("=" * 60)
print("CREDENTIAL VERIFICATION")
print("=" * 60)

# --- OpenAI ---
print("\n[1] Testing OpenAI API key...")
if not OPENAI_API_KEY:
    print("  ERROR: OPENAI_API_KEY not set. Check secrets/.env")
    sys.exit(1)
key_prefix = OPENAI_API_KEY[:10] + "..." + OPENAI_API_KEY[-4:]
print(f"  Key loaded: {key_prefix}")
print(f"  Model: {LLM_MODEL}")

try:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": "Reply with the single word: VERIFIED"}],
        max_tokens=10,
        temperature=0,
    )
    reply = resp.choices[0].message.content.strip()
    print(f"  API response: '{reply}'")
    print("  [PASS] OpenAI API is working")
except Exception as e:
    print(f"  [FAIL] OpenAI API error: {e}")
    sys.exit(1)

# --- JSL ---
print("\n[2] Checking JSL license file...")
if not JSL_LICENSE_PATH:
    print("  WARN: JSL_LICENSE_PATH not set — Pipeline A will use LLM-enhanced mode")
elif not Path(JSL_LICENSE_PATH).exists():
    print(f"  ERROR: JSL license file not found at {JSL_LICENSE_PATH}")
else:
    try:
        with open(JSL_LICENSE_PATH) as f:
            lic = json.load(f)
        token = lic.get("SPARK_NLP_LICENSE", "")
        print(f"  Token loaded: {token[:20]}...{token[-10:]}")
        print("  [PASS] JSL license file readable")
    except Exception as e:
        print(f"  [FAIL] Could not read JSL license: {e}")

print("\n[3] Testing JSL/Spark availability...")
try:
    import johnsnowlabs
    print(f"  johnsnowlabs version: {johnsnowlabs.__version__}")
    # Try to start spark with license
    import sparknlp_jsl
    spark = sparknlp_jsl.start(license_keys_path=JSL_LICENSE_PATH, gpu=False)
    print(f"  [PASS] Spark started: version {spark.version}")
    spark.stop()
except ImportError as e:
    print(f"  [SKIP] JSL not installed ({e}) — Pipeline A will use LLM-enhanced mode")
except Exception as e:
    print(f"  [SKIP] JSL startup failed ({type(e).__name__}: {e}) — Pipeline A will use LLM-enhanced mode")

print("\nVERIFICATION COMPLETE")
