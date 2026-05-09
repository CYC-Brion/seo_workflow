@echo off
cd /d "D:\工作流项目"
set LOGFILE=D:\工作流项目\data\logs\auto_publish.log
echo [%date% %time%] Starting publish-next... >> "%LOGFILE%"
D:\Python\python.exe -m src.cli.main workflow publish-next >> "%LOGFILE%" 2>&1
echo [%date% %time%] Exit code: %ERRORLEVEL% >> "%LOGFILE%"
