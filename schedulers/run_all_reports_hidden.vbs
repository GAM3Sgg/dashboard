Set WshShell = CreateObject("WScript.Shell")
' Run all gaming reports (Telegram + dashboard rebuild + git push) in one go
WshShell.Run "cmd /c set PYTHONIOENCODING=utf-8 && """"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe"""" """"C:\Users\User\clawd\scripts\run_all_reports.py""""""", 0, False
