@echo off
rem Opens this computer's copy of the map in the default browser (the version not yet published).
rem Keep the black window open while looking at the map; close it to stop.
cd /d "%~dp0"
python make.py preview
if errorlevel 1 pause
