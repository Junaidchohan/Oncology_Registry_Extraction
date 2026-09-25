@echo off
call python -m venv venv_jsl
call .\venv_jsl\Scripts\activate.bat
call python -m pip install --upgrade pip setuptools wheel
call pip install johnsnowlabs==5.4.1
echo --- STEP 5: JSL INSTALL ---
call python -c "from johnsnowlabs import nlp; nlp.install(licenses_file='secrets/jsl_license.json')"
echo --- STEP 6: IMPORT TEST ---
call python -c "import sparknlp_jsl; print('sparknlp_jsl OK')"
echo --- STEP 7: MINIMAL PIPELINE TEST ---
call python -c "from sparknlp_jsl.start import start; spark = start(license_path='secrets/jsl_license.json', gpu=False); print('JSL started:', spark.version)"
