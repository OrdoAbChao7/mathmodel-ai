@echo off
python analysis\run.py --compile %*
exit /b %ERRORLEVEL%
