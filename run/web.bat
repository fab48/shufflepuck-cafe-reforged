@echo off
rem Lance le prototype web : http://localhost:8731
cd /d "%~dp0..\web"
start "" http://localhost:8731
python -m http.server 8731
