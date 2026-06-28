@echo off
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required. Install uv or run: python app.py
  pause
  exit /b 1
)
uv run semcl-studio
if errorlevel 1 pause

