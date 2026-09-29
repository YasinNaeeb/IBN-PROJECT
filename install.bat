@echo off
echo ============================================
echo   IBN ChatOps - Installing dependencies
echo ============================================
echo.
pip install -r requirements.txt
echo.
echo ============================================
echo   Done! Now:
echo   1. Edit config.py with your settings
echo   2. Copy ibn_dleberta into models/
echo   3. Run start_all.bat
echo ============================================
pause
