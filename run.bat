
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
py manage.py runserver
pause
