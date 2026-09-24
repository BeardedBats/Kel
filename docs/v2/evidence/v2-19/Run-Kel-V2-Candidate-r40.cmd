@echo off
REM Kel V2 r40 candidate - isolated host, store, and engine roots.
set "KEL_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\r40\engine"
set "AIONUI_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\r40\store"
set "KEL_HOST_DATA_DIR=C:\Users\Nick\KelV2Runs\prepared\r40\host"
set "KEL_PROTECTED_PATHS=C:\Users\Nick\KelDogfoodCandidate;C:\Users\Nick\KelV2Candidate"
start "" "%~dp0Kel.exe"
