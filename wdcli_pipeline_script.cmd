SET APP_REFERENCE_ID=security_analyzer_kkvxdf
SET APP_DIRECTORY=%cd%
SET WDCLI_PIPELINE_DIR=C:\wdcli_pipeline
 
 
cmd /c wdcli app download "%APP_REFERENCE_ID%" -d "%APP_DIRECTORY%\archive" --latest-version --overwrite --as-zip
 
if %errorlevel% neq 0 cmd /c wdcli auth login
 
cmd /c py "%WDCLI_PIPELINE_DIR%\wdcli_pipeline.py" "%APP_DIRECTORY%" 
 
PAUSE
