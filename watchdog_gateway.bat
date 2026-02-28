@echo off
:: OpenClaw Gateway Watchdog - checks if gateway is running, restarts if not (hidden)
tasklist /FI "IMAGENAME eq node.exe" 2>NUL | findstr /I "openclaw" >NUL
if errorlevel 1 (
    wscript.exe "C:\Users\User\.openclaw\gateway_hidden.vbs"
)
