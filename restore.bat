@echo off
rem Undo everything tv.py changed, from the latest backup (Windows). Emergency: restore.bat --only dns
python "%~dp0tv.py" restore %*
