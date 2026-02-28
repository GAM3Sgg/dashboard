Set WshShell = CreateObject("WScript.Shell")
' Run Gaming Trends report and wait for completion
WshShell.Run "cmd /c set PYTHONIOENCODING=utf-8 && """"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe"""" """"C:\Users\User\clawd\scripts\send_gaming_trends_telegram.py""""""", 0, True
' Then rebuild dashboard data and push to GitHub
WshShell.Run "cmd /c set PYTHONIOENCODING=utf-8 && """"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe"""" """"C:\Users\User\clawd\scripts\build_dashboard.py"""" --push", 0, False
