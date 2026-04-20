"""
主線車輛規劃系統 - ��間估算
"""
from config import SPEED_PROFILES, ROAD_TYPE_KEYWORDS, MODULE_CONFIGS


def classify_road_type(address: str) -> str:
    """根據地址關鍵字判斷道路類型"""
    if not address:
        return "urban"

    for road_type, keywords in ROAD_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in address:
                return road_type
    return "urban"


def estimate_travel_time_hours(distance_km: float, road_type: str = "urban") -> float:
    """
    估算行駛時間（小時）。

    Parameters:
        distance_km: 距離（公里）
        road_type: 道路類型
    """
    speed = SPEED_PROFILES.get(road_type, SPEED_PROFILES["urban"])
    if speed == 0:
        return 0
    return distance_km / speed


def estimate_unload_time_hours(store_count: int, module: int) -> float:
    """
    估算卸貨總時間（小時）。

    Parameters:
        store_count: 門市數
        module: 模組編號
    """
    minutes_per_store = MODULE_CONFIGS[module]["unload_minutes_per_store"]
    total_minutes = store_count * minutes_per_store
    return total_minutes / 60.0


def estimate_route_time(route, geocoder) -> float:
    """
    估算整條路線的總時間（小時）。
    包含：倉庫→門市→...→門市→倉庫 的行駛時間 + 卸貨時間。

    Parameters:
        route: Route 物件
        geocoder: GeocoderService 實例

    Returns:
        總預估時間（小時）
    """
    if not route.stores:
        return 0

    total_distance = route.estimated_distance_km
    store_count = len(route.stores)

    # 估算平均道路類型（取最多門市的道路類型）
    road_types = [classify_road_type(s.address) for s in route.stores]
    road_type_counts = {}
    for rt in road_types:
        road_type_counts[rt] = road_type_counts.get(rt, 0) + 1
    primary_road_type = max(road_type_counts, key=road_type_counts.get)

    travel_time = estimate_travel_time_hours(total_distance, primary_road_type)
    unload_time = estimate_unload_time_hours(store_count, route.module)

    return travel_time + unload_time


def validate_time_constraint(route) -> list:
    """
    檢查路線是否符合時間限制。

    Returns:
        warnings 列表
    """
    warnings = []
    module_config = MODULE_CONFIGS[route.module]
    max_hours = module_config.get("max_hours")

    if max_hours and route.estimated_time_hours > max_hours:
        warnings.append(
            f"🔴 超過時間限制：預估 {route.estimated_time_hours:.1f} 小時 "
            f"（上限 {max_hours} 小時）"
        )
    elif max_hours and route.estimated_time_hours > max_hours * 0.9:
        warnings.append(
            f"⚠️ 接近時間上限：預估 {route.estimated_time_hours:.1f} 小時 "
            f"（上限 {max_hours} 小時）"
        )

    return warnings
