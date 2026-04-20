@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo  主線車輛規劃系統 - 套件安裝
echo ========================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.8 以上版本
    echo 下載網址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 正在安裝必要套件，請稍候...
echo.
pip install -r requirements.txt
echo.
if %errorlevel% neq 0 (
    echo [錯誤] 套件安裝失敗，請確認網路連線正常後重試。
) else (
    echo 安裝完成！現在可以執行程式了。
    echo 請雙擊「執行規劃程式.bat」或「啟動網頁介面.bat」。
)
echo.
pause
