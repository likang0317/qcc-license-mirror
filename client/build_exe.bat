@echo off
chcp 65001 >nul
cd /d "D:\work\trea工作空间\workspace\qcc-wechat\client"
echo [1/3] 清理旧产物...
rmdir /s /q build 2>nul
del /q QCC-WeChat.spec 2>nul
del /q dist\QCC-WeChat.exe 2>nul

echo [2/3] 开始打包...
"C:\Windows\py.exe" -m PyInstaller --onefile --windowed --name "QCC-WeChat" --add-data "certs;certs" --hidden-import="Crypto.Cipher.AES" --hidden-import="Crypto.Hash.SHA256" --hidden-import="Crypto.Signature.pkcs1_15" --hidden-import="openpyxl" --hidden-import="pyautogui" main.py

echo [3/3] 清理...
rmdir /s /q build 2>nul
del /q QCC-WeChat.spec 2>nul

echo ============================================
if exist "dist\QCC-WeChat.exe" (
    for %%A in ("dist\QCC-WeChat.exe") do echo ✅ 成功: dist\QCC-WeChat.exe  [%%~zA bytes]
    if not exist "dist\config" xcopy /E /I config dist\config >nul
    echo config 目录已就绪
) else (
    echo ❌ 打包失败
)
echo ============================================
pause
