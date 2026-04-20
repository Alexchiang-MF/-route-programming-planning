"""
主線車輛規劃系統 - 主程式入口
===========================================
大溪倉主線車輛規劃系統
- 讀取模組一/二/四的門市 Excel 資料
- 依序規劃三個模組的配送路線（共用車輛池）
- 輸出 Excel 規劃報表
"""
import sys
import os
import io
import time

# Windows 終端 UTF-8 輸出
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 確保能找到同目錄的模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_all_data
from geocoder import GeocoderService
from vehicle_pool import VehiclePool
from route_planner import RoutePlanner
from report_generator import generate_report
from config import MODULE_CONFIGS


def main():
    print("=" * 60)
    print("  主線車輛規劃系統")
    print("  大溪倉主線車輛規劃系統")
    print("=" * 60)

    start_time = time.time()

    # Step 1: 讀取所有 Excel 資料
    print("\n📂 Step 1: 讀取門市資料...")
    stores_by_module = load_all_data()

    total_stores = sum(len(v) for v in stores_by_module.values())
    if total_stores == 0:
        print("❌ 未讀取到任何門市資料，請檢查 Excel 檔案是否存在。")
        return

    # Step 2: 地理編碼
    print("\n🌍 Step 2: 地理編碼（離線模式：鄉鎮區中心座標）...")
    geocoder = GeocoderService()
    all_stores = []
    for stores in stores_by_module.values():
        all_stores.extend(stores)
    geocoded = geocoder.geocode_batch(all_stores)
    print(f"  完成 {geocoded} 間門市的座標定位")

    # Step 3: 初始化車輛池
    print("\n🚛 Step 3: 初始化車輛池...")
    pool = VehiclePool()
    print(f"  5噸車：{pool.available_5ton} 台可用")
    print(f"  8噸車：{pool.available_8ton} 台可用")

    # Step 4: 依序規劃三個模組
    print("\n📋 Step 4: 開始路線規劃...")
    planner = RoutePlanner(geocoder, pool)
    all_routes = []
    all_merge_reports = []

    for module in [1, 2, 4]:
        stores = stores_by_module.get(module, [])
        if not stores:
            print(f"\n  {MODULE_CONFIGS[module]['name']}：無門市資料，跳過")
            continue

        routes = planner.plan_module(module, stores)
        all_routes.extend(routes)

        # 顯示模組結果摘要
        mod_stores = sum(r.store_count for r in routes)
        mod_boxes = sum(r.total_boxes for r in routes)
        mod_dist = sum(r.estimated_distance_km for r in routes)
        mod_warnings = sum(len(r.warnings) for r in routes)
        cross_county = sum(1 for r in routes if r.is_cross_county)

        print(f"    → {len(routes)} 條路線, {mod_stores} 間門市, "
              f"{mod_boxes} 箱, {mod_dist:.0f} km")
        if cross_county:
            print(f"    → ⚡ {cross_county} 條跨縣市整併路線")
        if mod_warnings:
            print(f"    → ⚠️ {mod_warnings} 個警告事項")

        # 更新車輛狀態
        print(f"    → 剩餘車輛：5噸 {pool.available_5ton} 台, "
              f"8噸 {pool.available_8ton} 台")

    # Step 5: 產出報表
    print("\n📊 Step 5: 產出 Excel 報表...")
    report_path = generate_report(all_routes, pool, all_merge_reports)

    # 完成摘要
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("  規劃完成！")
    print("=" * 60)
    print(f"\n  總路線數：{len(all_routes)} 條")
    print(f"  總門市數：{sum(r.store_count for r in all_routes)} 間")
    print(f"  總箱數：{sum(r.total_boxes for r in all_routes)} 箱")
    print(f"  總里程：{sum(r.estimated_distance_km for r in all_routes):.0f} km")

    summary = pool.get_summary()
    print(f"\n  車輛使用：")
    print(f"    5噸車：{summary['used_5ton']}/{summary['total_5ton']} 台 "
          f"({summary['usage_5ton_pct']:.1f}%)")
    print(f"    8噸車：{summary['used_8ton']}/{summary['total_8ton']} 台 "
          f"({summary['usage_8ton_pct']:.1f}%)")

    warnings_count = sum(len(r.warnings) for r in all_routes)
    if warnings_count:
        print(f"\n  ⚠️ 共有 {warnings_count} 個警告事項，請查看報表「規劃備註」")

    print(f"\n  執行時間：{elapsed:.1f} 秒")
    print(f"  報表位置：{report_path}")


if __name__ == "__main__":
    main()
