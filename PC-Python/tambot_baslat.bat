@echo off
title Tambot
cd /d "%~dp0"
echo ============================================
echo  TAMBOT baslatiliyor
echo ============================================
echo adb forward tcp:30200 ayarlaniyor...
set "ADB=adb"
if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
if exist "C:\Program Files\platform-tools\adb.exe" set "ADB=C:\Program Files\platform-tools\adb.exe"
"%ADB%" forward tcp:30200 tcp:30200 >nul 2>&1
if errorlevel 1 (
  echo [uyari] adb forward yapilamadi.
  echo   - Telefon USB ile bagli ve USB hata ayiklama acik mi?
  echo   - Farkli konumdaysa: panelden "adb forward" dugmesini dene.
) else (
  echo adb forward TAMAM ^(tcp:30200 / %ADB%^)
)
echo.
echo Tambot penceresi aciliyor...
python tambot.py
echo.
echo Tambot kapandi. Kapatmak icin bir tusa bas.
pause >nul
