"""
主線車輛規劃系統 - 設定常數
"""
import os

# === 基本路徑 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# =====================================================
# 【資料來源資料夾設定】
# 若 Excel 資料檔與程式放在同一資料夾，保持 None 即可。
# 若資料檔放在其他位置，請修改為絕對路徑，例如：
#   DATA_DIR = r"D:\物流資料\每日配送"
# =====================================================
DATA_DIR = None  # None = 與程式同一資料夾

# === 倉庫資訊 ===
WAREHOUSE_NAME = "大溪倉"
WAREHOUSE_ADDRESS = "桃園市大溪區新光東路76巷22-2號"
WAREHOUSE_COORDS = (24.8834, 121.2868)  # (latitude, longitude)

# === 車輛規格（三個模組共用）===
VEHICLE_SPECS = {
    "5ton": {
        "name": "5噸車",
        "total_count": 82,
        "max_capacity": 160,
        "actual_capacity": 144,  # 90% of 160
        "target_stores_min": 16,
        "target_stores_max": 20,
        "suitable_keywords": ["巷", "弄", "山", "產業道路", "偏遠"],
    },
    "8ton": {
        "name": "8噸車",
        "total_count": 59,
        "max_capacity": 240,
        "actual_capacity": 216,  # 90% of 240
        "target_stores_min": 22,
        "target_stores_max": 26,
        "suitable_keywords": ["路", "街", "大道", "幹道"],
    },
}

# === 模組配置 ===
MODULE_CONFIGS = {
    1: {
        "name": "模組一",
        "description": "非24小時特殊路線",
        "label": "🌞 模組一：非24小時特殊路線",
        "time_window": "daytime",
        "max_hours": None,  # 依白天時段而定
        "cross_county": False,
        "priority": 1,
        "unload_minutes_per_store": 7.5,
    },
    2: {
        "name": "模組二",
        "description": "特定店舖配送",
        "label": "⚠️ 模組二：特定店舖（需注意作業溝通）",
        "time_window": (18, 7),  # 18:00-07:00
        "max_hours": 7,
        "cross_county": False,
        "priority": 2,
        "unload_minutes_per_store": 10.0,  # 7.5 + 2.5 buffer
    },
    4: {
        "name": "模組四",
        "description": "一般店舖配送",
        "label": "✅ 模組四：一般店舖配送",
        "time_window": (18, 7),  # 18:00-07:00
        "max_hours": 7,
        "cross_county": True,
        "priority": 3,
        "unload_minutes_per_store": 7.5,
    },
}

# === 跨縣市整併規則（僅模組四）===
CROSS_COUNTY_RULES = [
    {
        "county_a": "台北市",
        "county_b": "基隆市",
        "districts_a": ["南港區", "內湖區", "士林區"],
        "districts_b": None,  # None = 全部
        "description": "台北市北部區域與基隆市相鄰",
    },
    {
        "county_a": "台北市",
        "county_b": "新北市",
        "districts_a": None,
        "districts_b": None,
        "description": "台北市與新北市邊界區域",
    },
    {
        "county_a": "新北市",
        "county_b": "基隆市",
        "districts_a": ["瑞芳區", "汐止區"],
        "districts_b": None,
        "description": "新北市北部與基隆市相鄰",
    },
    {
        "county_a": "新北市",
        "county_b": "桃園市",
        "districts_a": ["三峽區", "樹林區", "鶯歌區"],
        "districts_b": None,
        "description": "新北市南部與桃園市相鄰",
    },
    {
        "county_a": "桃園市",
        "county_b": "新竹縣",
        "districts_a": None,
        "districts_b": None,
        "description": "桃園市南部與新竹縣北部相鄰",
    },
    {
        "county_a": "新竹市",
        "county_b": "新竹縣",
        "districts_a": None,
        "districts_b": None,
        "description": "新竹市與新竹縣為同一生活圈",
    },
    {
        "county_a": "宜蘭縣",
        "county_b": "花蓮縣",
        "districts_a": None,
        "districts_b": None,
        "description": "東部配送路線可順路整併",
    },
]

# === 跨縣市整併門檻 ===
MERGE_MILEAGE_REDUCTION_THRESHOLD = 0.10  # 里程減少 > 10%
MERGE_TIME_SAVINGS_THRESHOLD = 0.5  # 時間節省 > 0.5 小時

# === 速度參數 (km/h) ===
SPEED_PROFILES = {
    "highway": 90,      # 高速公路
    "provincial": 60,   # 省道/快速道路
    "urban": 35,        # 市區道路
    "alley": 25,        # 巷弄/山區
}

# === 道路類型判斷關鍵字 ===
ROAD_TYPE_KEYWORDS = {
    "highway": ["高速", "國道", "快速"],
    "provincial": ["省道", "台"],
    "alley": ["巷", "弄", "山", "產業道路"],
    # 預設為 urban
}

# === 道路距離修正係數（直線距離 × 係數 = 實際道路距離）===
ROAD_FACTOR = {
    "highway": 1.2,
    "provincial": 1.3,
    "urban": 1.4,
    "alley": 1.6,
    "default": 1.4,
}

# === Excel 欄位索引（0-based）===
COL_CATEGORY = 0       # 重組類別
COL_ROUTE = 1          # 現況路線
COL_ARRIVAL_TIME = 2   # 現況到店時間
COL_STORE_ID = 3       # 店號
COL_STORE_NAME = 4     # 店名
COL_COUNTY = 5         # 縣市
COL_WAREHOUSE = 6      # 倉別
COL_ADDRESS = 7        # 地址
COL_BOX_START = 8      # 出貨箱數起始欄
COL_BOX_END = 14       # 出貨箱數結束欄（含）

# === 輸入檔案對應 ===
INPUT_FILES = {
    "module1": "模組一特殊路線.xlsx",
    "module2": "模組二特殊店.xlsx",
    "module4_taipei": "模組四台北.xlsx",
    "module4_newtaipei": "模組四新北.xlsx",
    "module4_keelung": "模組四基隆.xlsx",
    "module4_yilan": "模組四宜蘭.xlsx",
    "module4_hsinchu": "模組四新竹.xlsx",
    "module4_taoyuan": "模組四桃園.xlsx",
    "module4_miaoli": "模組四苗栗.xlsx",
}

# === 縣市名稱標準化對應 ===
COUNTY_NORMALIZE = {
    "桃園縣": "桃園市",
    "新竹縣市": "新竹縣",
}

# === 各縣市預期店舖數（參考）===
COUNTY_STORE_COUNTS = {
    "新北市": 953,
    "台北市": 636,
    "桃園市": 422,
    "新竹縣": 133,
    "新竹市": 113,
    "宜蘭縣": 82,
    "基隆市": 71,
    "花蓮縣": 59,
    "苗栗縣": 56,
}
