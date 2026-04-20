"""
主線車輛規劃系統 - 地理編碼與距離計算
"""
import math
import hashlib
import numpy as np
from district_coords import DISTRICT_COORDS, COUNTY_COORDS
from config import WAREHOUSE_COORDS, ROAD_FACTOR


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Haversine 公式計算兩點間的直線距離（公里）。
    """
    R = 6371  # 地球半徑（公里）
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def _address_jitter(store_id: str, base_lat: float, base_lon: float):
    """
    根據 store_id 產生確定性的微小偏移，區分同區門市。
    偏移量約 ±0.005 度（~500m），足以區分同區門市的相對位置���
    """
    h = hashlib.md5(store_id.encode()).hexdigest()
    lat_offset = (int(h[:8], 16) / 0xFFFFFFFF - 0.5) * 0.01
    lon_offset = (int(h[8:16], 16) / 0xFFFFFFFF - 0.5) * 0.01
    return base_lat + lat_offset, base_lon + lon_offset


class GeocoderService:
    """地理編碼服務（離線模式：使用鄉鎮區中心座標）"""

    def __init__(self):
        self.coords_cache = {}

    def geocode_store(self, store):
        """為單一門市設定經緯度座標"""
        if store.latitude != 0 and store.longitude != 0:
            return  # 已有座標

        # 嘗試用「縣市+區」查找
        key = f"{store.county}{store.district}"
        if key in DISTRICT_COORDS:
            base_lat, base_lon = DISTRICT_COORDS[key]
            store.latitude, store.longitude = _address_jitter(
                store.store_id, base_lat, base_lon
            )
            return

        # 嘗試只用縣市查找
        if store.county in COUNTY_COORDS:
            base_lat, base_lon = COUNTY_COORDS[store.county]
            store.latitude, store.longitude = _address_jitter(
                store.store_id, base_lat, base_lon
            )
            return

        # 最後備用：使用倉庫座標
        store.latitude, store.longitude = _address_jitter(
            store.store_id, WAREHOUSE_COORDS[0], WAREHOUSE_COORDS[1]
        )

    def geocode_batch(self, stores: list):
        """批次地理編碼所有門市"""
        geocoded = 0
        for store in stores:
            self.geocode_store(store)
            geocoded += 1
        return geocoded

    def get_distance_km(self, store1, store2, road_type="default"):
        """
        計算兩門市間的估算道路距離（公里）。
        直線距離 × 道路修正係數。
        """
        straight = haversine_distance(
            store1.latitude, store1.longitude,
            store2.latitude, store2.longitude
        )
        factor = ROAD_FACTOR.get(road_type, ROAD_FACTOR["default"])
        return straight * factor

    def get_distance_from_warehouse(self, store, road_type="default"):
        """計算門市與大溪倉的距離"""
        straight = haversine_distance(
            WAREHOUSE_COORDS[0], WAREHOUSE_COORDS[1],
            store.latitude, store.longitude
        )
        factor = ROAD_FACTOR.get(road_type, ROAD_FACTOR["default"])
        return straight * factor

    def get_angle_from_warehouse(self, store) -> float:
        """
        計算門市相對大溪倉的方位角（度，0=正北，順時針）。
        用於同心圓模式的圓掃排序。
        """
        dlat = store.latitude  - WAREHOUSE_COORDS[0]
        dlon = store.longitude - WAREHOUSE_COORDS[1]
        # atan2(east, north) → 從正北順時針
        angle = math.degrees(math.atan2(dlon, dlat))
        return angle % 360  # 轉為 0-360

    def get_ring(self, store) -> int:
        """
        取得門市所屬同心圓環帶。
        Ring 1: 0-20km, Ring 2: 20-35km, Ring 3: 35-50km, Ring 4: 50km+
        """
        dist = self.get_distance_from_warehouse(store)
        if dist < 20:
            return 1
        elif dist < 35:
            return 2
        elif dist < 50:
            return 3
        else:
            return 4

    def build_distance_matrix(self, stores: list):
        """
        建構門市間的距離矩陣（含倉庫）。

        Returns:
            numpy array, shape (n+1, n+1)
            index 0 = 倉庫, index 1..n = stores
        """
        n = len(stores)
        matrix = np.zeros((n + 1, n + 1))

        # 所有點的座標（倉庫 + 門市）
        coords = [(WAREHOUSE_COORDS[0], WAREHOUSE_COORDS[1])]
        for s in stores:
            coords.append((s.latitude, s.longitude))

        factor = ROAD_FACTOR["default"]
        for i in range(n + 1):
            for j in range(i + 1, n + 1):
                dist = haversine_distance(
                    coords[i][0], coords[i][1],
                    coords[j][0], coords[j][1]
                ) * factor
                matrix[i][j] = dist
                matrix[j][i] = dist

        return matrix
