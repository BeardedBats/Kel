@echo off
REM Kel V2 r29 candidate - isolated engine root and desktop store.
set "KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\r29\engine"
set "AIONUI_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\r29\store"
set "KEL_HOST_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\r29\host"
set "KEL_PROTECTED_PATHS=C:\Users\Nick\KelDogfoodCandidate;C:\Users\Nick\KelV2Candidate"
start "" "%~dp0Kel.exe"
