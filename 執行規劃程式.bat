@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo  主線車輛規劃系統
echo ========================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.8 以上版本
    echo 下載網址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 正在執行，請稍候約 1 分鐘...
echo.
python main.py
echo.
if %errorlevel% neq 0 (
    echo [錯誤] 程式執行失敗，錯誤碼: %errorlevel%
) else (
    echo 完成！請至 output 資料夾查看報表。
)
echo.
pause
