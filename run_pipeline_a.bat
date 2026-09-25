powershell -ExecutionPolicy Bypass -Command "
cd 'e:\AI Projects\Oncology Registry Extraction'
. .\setup_jsl_env.ps1
python src\pipeline_a_classical\run_jsl.py --report-id report_001
"
