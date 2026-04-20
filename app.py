"""
主線車輛規劃系統 - Flask Web 介面
"""
import sys
import os
import io
import uuid
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_file
from data_loader import load_excel_file
from geocoder import GeocoderService
from vehicle_pool import VehiclePool
from route_planner import RoutePlanner, MODE_LOOP, MODE_RING
from report_generator import generate_report
from config import OUTPUT_DIR

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# 工作狀態儲存 {job_id: {status, logs, result, file_path}}
jobs = {}

FILE_KEY_MAP = {
    "m1":          (1, "module1"),
    "m2":          (2, "module2"),
    "m4-taipei":   (4, "module4_taipei"),
    "m4-newtaipei":(4, "module4_newtaipei"),
    "m4-keelung":  (4, "module4_keelung"),
    "m4-yilan":    (4, "module4_yilan"),
    "m4-hsinchu":  (4, "module4_hsinchu"),
    "m4-taoyuan":  (4, "module4_taoyuan"),
    "m4-miaoli":   (4, "module4_miaoli"),
    "m4-hualien":  (4, "module4_hualien"),
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start():
    """接收上傳檔案，啟動背景規劃工作"""
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "logs": [], "result": None, "file_path": None}

    # 儲存上傳的檔案到暫存目錄
    upload_dir = os.path.join(OUTPUT_DIR, f"uploads_{job_id}")
    os.makedirs(upload_dir, exist_ok=True)

    uploaded = {}
    for key in request.files:
        f = request.files[key]
        if f.filename:
            save_path = os.path.join(upload_dir, f"{key}.xlsx")
            f.save(save_path)
            uploaded[key] = save_path

    if not uploaded:
        return jsonify({"error": "未收到任何檔案"}), 400

    # 讀取規劃參數
    route_mode = request.form.get("route_mode", "loop")
    if route_mode not in ("loop", "ring"):
        route_mode = "loop"
    load_rate_pct = float(request.form.get("load_rate", 90))
    load_rate = max(50, min(100, load_rate_pct)) / 100.0

    # 背景執行規劃
    t = threading.Thread(target=run_planning,
                         args=(job_id, uploaded, route_mode, load_rate))
    t.daemon = True
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    """查詢工作狀態，並回傳新的 log 行"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404

    # 取出尚未回傳的 logs
    sent_key = f"_sent_{job_id}"
    sent = jobs.get(sent_key, 0)
    new_logs = job["logs"][sent:]
    jobs[sent_key] = sent + len(new_logs)

    return jsonify({
        "status": job["status"],
        "logs": new_logs,
        "result": job["result"],
        "error": job.get("error"),
    })


@app.route("/api/download/<job_id>")
def download(job_id):
    """下載規劃報表"""
    job = jobs.get(job_id)
    if not job or not job.get("file_path"):
        return "找不到報表", 404
    return send_file(
        job["file_path"],
        as_attachment=True,
        download_name="路線規劃報告.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def run_planning(job_id: str, uploaded: dict,
                 route_mode: str = "loop", load_rate: float = 0.9):
    """背景執行路線規劃"""
    job = jobs[job_id]

    def log(msg):
        job["logs"].append(msg)

    try:
        log("📂 Step 1: 讀取門市資料...")

        stores_by_module = {1: [], 2: [], 4: []}

        for key, filepath in uploaded.items():
            if key not in FILE_KEY_MAP:
                continue
            module, _ = FILE_KEY_MAP[key]
            stores = load_excel_file(filepath, module)
            stores_by_module[module].extend(stores)
            label = {1: "模組一", 2: "模組二", 4: "模組四"}.get(module, "")
            county_name = key.replace("m4-", "").replace("m1", "").replace("m2", "")
            log(f"  {label} {county_name}：{len(stores)} 間門市")

        total = sum(len(v) for v in stores_by_module.values())
        log(f"  總計：{total} 間門市（模組一:{len(stores_by_module[1])} 模組二:{len(stores_by_module[2])} 模組四:{len(stores_by_module[4])}）")

        if total == 0:
            job["status"] = "error"
            job["error"] = "未讀取到任何門市資料"
            return

        log("🌍 Step 2: 地理編碼（離線模式）...")
        geocoder = GeocoderService()
        all_stores = []
        for stores in stores_by_module.values():
            all_stores.extend(stores)
        geocoder.geocode_batch(all_stores)
        log(f"  完成 {len(all_stores)} 間門市座標定位")

        log("🚛 Step 3: 初始化車輛池...")
        pool = VehiclePool()
        log(f"  5噸車 {pool.available_5ton} 台 / 8噸車 {pool.available_8ton} 台")

        mode_label = "迴圈模式" if route_mode == MODE_LOOP else "同心圓模式"
        log(f"⚙️ 路線模式：{mode_label}　裝載率：{load_rate*100:.0f}%")
        log(f"  5噸車有效容量：{int(160*load_rate)} 箱　8噸車有效容量：{int(240*load_rate)} 箱")

        log("📋 Step 4: 開始路線規劃...")
        planner = RoutePlanner(geocoder, pool,
                               route_mode=route_mode, load_rate=load_rate)
        all_routes = []

        for module in [1, 2, 4]:
            stores = stores_by_module.get(module, [])
            if not stores:
                continue

            from config import MODULE_CONFIGS
            name = MODULE_CONFIGS[module]["name"]
            log(f"  規劃{name}（{len(stores)} 間門市）...")

            routes = planner.plan_module(module, stores)
            all_routes.extend(routes)

            mod_stores = sum(r.store_count for r in routes)
            mod_km = sum(r.estimated_distance_km for r in routes)
            cross = sum(1 for r in routes if r.is_cross_county)
            warns = sum(len(r.warnings) for r in routes)

            log(f"  ✅ {len(routes)} 條路線, {mod_stores} 間門市, {mod_km:.0f} km")
            if cross:
                log(f"  ⚡ {cross} 條跨縣市整併路線")
            if warns:
                log(f"  ⚠️ {warns} 個警告事項")
            log(f"  → 剩餘：5噸 {pool.available_5ton} 台 / 8噸 {pool.available_8ton} 台")

        log("📊 Step 5: 產出 Excel 報表...")
        report_path = generate_report(all_routes, pool, [],
                                      route_mode=route_mode,
                                      load_rate=load_rate)
        job["file_path"] = report_path

        summary = pool.get_summary()
        total_warns = sum(len(r.warnings) for r in all_routes)

        job["result"] = {
            "total_routes": len(all_routes),
            "total_stores": sum(r.store_count for r in all_routes),
            "total_boxes":  sum(r.total_boxes for r in all_routes),
            "total_km":     round(sum(r.estimated_distance_km for r in all_routes), 0),
            "used_5ton":    summary["used_5ton"],
            "used_8ton":    summary["used_8ton"],
            "total_5ton":   summary["total_5ton"],
            "total_8ton":   summary["total_8ton"],
            "warnings":     total_warns,
        }
        job["status"] = "done"
        log(f"🎉 規劃完成！共 {len(all_routes)} 條路線，報表已產出。")

    except Exception as e:
        import traceback
        job["status"] = "error"
        job["error"] = str(e)
        job["logs"].append(f"❌ 錯誤：{e}")
        job["logs"].append(traceback.format_exc())


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 50)
    print("  主線車輛規劃系統 - Web 介面")
    print("  請用瀏覽器開啟：http://localhost:5001")
    print("  按 Ctrl+C 可關閉伺服器")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5001, debug=False)
