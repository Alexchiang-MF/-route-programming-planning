# 主線車輛規劃系統

大溪倉主線車輛規劃系統 — 依據每日出貨箱數，自動將門市分組編成配送路線、分派車輛、產出 Excel 規劃報表。

## 功能特色

- 🌞 **模組一**：非 24 小時特殊路線（白天時段）
- ⚠️ **模組二**：特定店舖配送（18:00–07:00，需注意作業溝通）
- ✅ **模組四**：一般店舖配送（18:00–07:00，支援跨縣市整併）
- 🚛 **車隊管理**：5 噸車 82 台 + 8 噸車 59 台，智慧分派
- 🗺️ **兩種路線模式**：迴圈模式（TSP 最短路徑）／ 同心圓模式（70% 行政區 + 30% 環帶掃描）
- 📊 **雙介面**：命令列批次執行 + Flask 網頁上傳介面
- 📈 Excel 報表：路線明細、車輛使用、跨縣市整併、警告事項

## 快速開始

詳見 [下載安裝說明書.md](下載安裝說明書.md)

```bash
# 1. 複製專案
git clone https://github.com/Alexchiang-MF/-route-programming-planning.git

# 2. 安裝套件（Windows 雙擊）
安裝套件.bat

# 3. 將 Excel 資料檔放入資料夾後執行
執行規劃程式.bat          # CLI 模式
啟動網頁介面.bat          # 網頁模式（http://localhost:5001）
```

## 系統需求

- Windows 10 / 11（64 位元）
- Python 3.8 以上

## 專案結構

| 檔案 | 說明 |
|------|------|
| `main.py` | CLI 主程式入口 |
| `app.py` | Flask 網頁介面 |
| `config.py` | 車隊、模組、跨縣市規則設定 |
| `models.py` | 資料模型（Store / Vehicle / Route） |
| `data_loader.py` | Excel 讀取 |
| `geocoder.py` | 離線地理編碼（鄉鎮區中心座標） |
| `route_planner.py` | 核心路線規劃（TSP + 同心圓） |
| `vehicle_pool.py` | 車隊管理 |
| `cross_county.py` | 跨縣市整併邏輯 |
| `time_estimator.py` | 配送時間估算 |
| `report_generator.py` | Excel 報表產出 |
| `district_coords.py` | 全台鄉鎮區中心座標表 |

## 資料檔案

本 repo **不包含** 實際門市 Excel 資料（已於 `.gitignore` 排除）。使用前請將下列檔案放入專案資料夾：

- 模組一特殊路線.xlsx
- 模組二特殊店.xlsx
- 模組四台北.xlsx、新北、基隆、宜蘭、新竹、桃園、苗栗.xlsx

## 授權

內部使用
