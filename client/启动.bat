@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist "dist\QCC-WeChat.exe" (
    start "" "dist\QCC-WeChat.exe"
) else (
    echo [开发模式] 未找到 exe，使用 Python 直接运行...
    py -3 main.py
)
