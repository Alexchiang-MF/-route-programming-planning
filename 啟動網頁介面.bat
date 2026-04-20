@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo  主線車輛規劃系統 - 網頁介面
echo ========================================
echo.
echo 正在啟動伺服器...
echo 啟動後請用瀏覽器開啟：http://localhost:5001
echo.
echo 關閉此視窗即可停止伺服器。
echo.
start "" "http://localhost:5001"
python app.py
pause
