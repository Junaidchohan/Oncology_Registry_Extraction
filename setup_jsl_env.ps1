$env:JAVA_HOME   = "C:\Program Files\Eclipse Adoptium\jdk-11.0.32.101-hotspot"
$env:HADOOP_HOME = "C:\hadoop"
$env:TEMP        = "C:\temp"
$env:TMP         = "C:\temp"
$env:Path        = "$env:JAVA_HOME\bin;$env:HADOOP_HOME\bin;$env:Path"

# Load JSL license keys from cached license file
$licenseFile = "C:\Users\junai\.johnsnowlabs\licenses\license_number_0_for_Spark-Healthcare.json"
if (Test-Path $licenseFile) {
    $lic = Get-Content $licenseFile | ConvertFrom-Json
    $env:SPARK_NLP_LICENSE      = $lic.HC_LICENSE
    $env:JSL_NLP_LICENSE        = $lic.HC_LICENSE
    $env:AWS_ACCESS_KEY_ID      = $lic.AWS_ACCESS_KEY_ID
    $env:AWS_SECRET_ACCESS_KEY  = $lic.AWS_SECRET_ACCESS_KEY
    Write-Host "  License JWT loaded from $licenseFile" -ForegroundColor Cyan
} else {
    Write-Warning "License file not found: $licenseFile"
}

if (Test-Path ".\venv_jsl\Scripts\Activate.ps1") { . .\venv_jsl\Scripts\Activate.ps1 }
Write-Host "JSL environment ready." -ForegroundColor Green

