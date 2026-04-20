"""
主線車輛規劃系統 - 核心路線規劃演算法

支援兩種路線模式：
  迴圈模式 (loop)   : Nearest Neighbor + 2-opt TSP，優化最短總里程
  同心圓模式 (ring) : 以距離環帶+方位角掃描分組，70%行政區+30%同心圓補充
"""
import math
import numpy as np
from models import Route
from config import VEHICLE_SPECS, MODULE_CONFIGS, WAREHOUSE_COORDS
from cross_county import CrossCountyConsolidator
from time_estimator import estimate_route_time, validate_time_constraint

# 路線模式常數
MODE_LOOP = "loop"   # 迴圈模式（現有 TSP）
MODE_RING = "ring"   # 同心圓模式


class RoutePlanner:
    """路線規劃核心引擎"""

    def __init__(self, geocoder, vehicle_pool, route_mode: str = MODE_LOOP,
                 load_rate: float = 0.9):
        """
        Parameters:
            geocoder     : GeocoderService 實例
            vehicle_pool : VehiclePool 實例
            route_mode   : "loop" 或 "ring"
            load_rate    : 裝載率上限，0.0~1.0（預設 0.9）
        """
        self.geocoder = geocoder
        self.pool = vehicle_pool
        self.route_mode = route_mode
        self.load_rate = max(0.5, min(1.0, load_rate))
        self._route_counter = 0

        # 根據裝載率動態計算有效容量
        self.effective_capacity = {
            "5ton": int(VEHICLE_SPECS["5ton"]["max_capacity"] * self.load_rate),
            "8ton": int(VEHICLE_SPECS["8ton"]["max_capacity"] * self.load_rate),
        }

    def plan_module(self, module: int, stores: list) -> list:
        """
        規劃單一模組的所有路線。

        Parameters:
            module : 模組編號 (1, 2, 4)
            stores : 該模組的所有門市

        Returns:
            list[Route]
        """
        if not stores:
            return []

        config = MODULE_CONFIGS[module]
        mode_label = "迴圈模式" if self.route_mode == MODE_LOOP else "同心圓模式"
        print(f"\n  規劃{config['name']}（{len(stores)} 間門市，{mode_label}，"
              f"裝載率 {self.load_rate*100:.0f}%）...")

        # Step 1: 按縣市分組
        stores_by_county = {}
        for s in stores:
            stores_by_county.setdefault(s.county, []).append(s)

        # Step 2: 模組四跨縣市整併
        merge_reports = []
        if config["cross_county"]:
            consolidator = CrossCountyConsolidator(self.geocoder)
            groups, merge_reports = consolidator.execute_merges(stores_by_county)
            for r in merge_reports:
                if r["viable"]:
                    print(f"    ⚡ {r['reason']}")
        else:
            groups = stores_by_county

        # Step 3: 按模式分組並規劃
        all_routes = []
        for group_key, group_stores in groups.items():
            if self.route_mode == MODE_RING:
                routes = self._plan_ring_mode(module, group_key, group_stores)
            else:
                routes = self._plan_loop_mode(module, group_key, group_stores)
            all_routes.extend(routes)

        # Step 4: 計算時間 + 驗證約束
        for route in all_routes:
            route.estimated_time_hours = estimate_route_time(route, self.geocoder)
            route.warnings.extend(validate_time_constraint(route))

        print(f"    完成：{len(all_routes)} 條路線")
        return all_routes

    # =========================================================
    # 迴圈模式 (Loop Mode)
    # =========================================================

    def _plan_loop_mode(self, module: int, group_key: str,
                         stores: list) -> list:
        """迴圈模式：FFD 裝箱 + Nearest Neighbor + 2-opt TSP"""
        is_cross = "+" in group_key
        sorted_stores = sorted(stores, key=lambda s: s.avg_boxes, reverse=True)
        routes = []
        unassigned = list(sorted_stores)

        while unassigned:
            route_stores, unassigned = self._pack_one_route(module, unassigned)
            if not route_stores:
                route_stores, unassigned = unassigned[:1], unassigned[1:]

            route = self._build_route(module, route_stores, is_cross)
            # 路線序優化：TSP
            if module == 1:
                route.stores = self._sort_by_arrival_time(route.stores)
            else:
                route.stores = self._tsp_optimize(route.stores)
            route.estimated_distance_km = self._calc_distance(route.stores)
            routes.append(route)

        return routes

    # =========================================================
    # 同心圓模式 (Ring Mode)
    # =========================================================

    def _plan_ring_mode(self, module: int, group_key: str,
                         stores: list) -> list:
        """
        同心圓模式：
        - 70% 行政區配送：同一行政區門市優先組成路線
        - 30% 同心圓補充：剩餘門市依距離環帶 + 方位角補入路線
        - 路線排序：依方位角順時針掃描（圓掃順序）
        """
        is_cross = "+" in group_key

        # 計算每間門市的環帶與角度
        for s in stores:
            s._ring  = self.geocoder.get_ring(s)
            s._angle = self.geocoder.get_angle_from_warehouse(s)

        # === 分配配額 ===
        total = len(stores)
        district_quota = math.ceil(total * 0.70)  # 70% 行政區
        ring_quota     = total - district_quota    # 30% 同心圓

        # 按行政區分組
        by_district = {}
        for s in stores:
            by_district.setdefault(s.district or s.county, []).append(s)

        # 行政區配額：取各區前 70% 的門市（依箱數排序）
        district_stores = []
        ring_pool = []  # 同心圓補充池
        for district, dstores in by_district.items():
            sorted_d = sorted(dstores, key=lambda s: s.avg_boxes, reverse=True)
            cut = max(1, math.ceil(len(sorted_d) * 0.70))
            district_stores.extend(sorted_d[:cut])
            ring_pool.extend(sorted_d[cut:])

        # 若行政區門市超過配額，多餘的移入同心圓池
        if len(district_stores) > district_quota:
            overflow = district_stores[district_quota:]
            district_stores = district_stores[:district_quota]
            ring_pool.extend(overflow)

        # 同心圓池：依環帶→角度排序
        ring_pool.sort(key=lambda s: (s._ring, s._angle))

        # === 建立路線 ===
        routes = []

        # Phase A：用行政區門市建立主幹路線（FFD 裝箱）
        main_routes = []
        sorted_dist = sorted(district_stores, key=lambda s: s.avg_boxes, reverse=True)
        unassigned = list(sorted_dist)
        while unassigned:
            batch, unassigned = self._pack_one_route(module, unassigned)
            if not batch:
                batch, unassigned = unassigned[:1], unassigned[1:]
            main_routes.append(batch)

        # Phase B：將同心圓補充池的門市補入已有路線（不超載）
        for s in ring_pool:
            placed = False
            # 找最近且有容量的路線
            best_route_idx = -1
            best_dist = float('inf')
            for idx, batch in enumerate(main_routes):
                cur_boxes = sum(x.avg_boxes for x in batch)
                cap = self._get_capacity_for_batch(batch)
                if cur_boxes + s.avg_boxes > cap:
                    continue
                # 計算此門市到路線中心的距離
                center_lat = sum(x.latitude  for x in batch) / len(batch)
                center_lon = sum(x.longitude for x in batch) / len(batch)
                d = math.sqrt((s.latitude - center_lat)**2 +
                              (s.longitude - center_lon)**2)
                if d < best_dist:
                    best_dist = d
                    best_route_idx = idx
            if best_route_idx >= 0:
                main_routes[best_route_idx].append(s)
                placed = True
            if not placed:
                # 無法補入現有路線，開新路線
                main_routes.append([s])

        # Phase C：轉換為 Route 物件，路線排序依方位角（圓掃）
        for batch in main_routes:
            route = self._build_route(module, batch, is_cross)
            if module == 1:
                route.stores = self._sort_by_arrival_time(route.stores)
            else:
                # 同心圓排序：依環帶→方位角順時針
                route.stores = sorted(
                    route.stores,
                    key=lambda s: (getattr(s, '_ring', 0), getattr(s, '_angle', 0))
                )
            route.estimated_distance_km = self._calc_distance(route.stores)
            routes.append(route)

        return routes

    def _get_capacity_for_batch(self, batch: list) -> int:
        """取得一批門市對應的車輛有效容量"""
        total_boxes = sum(s.avg_boxes for s in batch)
        if total_boxes > self.effective_capacity["5ton"]:
            return self.effective_capacity["8ton"]
        return self.effective_capacity["5ton"]

    # =========================================================
    # 共用：車輛建立 / 裝箱 / TSP
    # =========================================================

    def _build_route(self, module: int, route_stores: list,
                     is_cross: bool) -> Route:
        """建立 Route 物件，分配車輛並驗證約束"""
        total_boxes = sum(s.avg_boxes for s in route_stores)
        addresses = [s.address for s in route_stores]
        vtype = self.pool.choose_vehicle_type(total_boxes, len(route_stores), addresses)
        vehicle = self.pool.allocate(vtype, module)
        if vehicle is None:
            alt = "8ton" if vtype == "5ton" else "5ton"
            vehicle = self.pool.allocate(alt, module)
        if vehicle is None:
            vehicle = self._dummy_vehicle(module)

        self._route_counter += 1
        route = Route(
            route_id=f"R-{self._route_counter:03d}",
            vehicle=vehicle,
            module=module,
            stores=list(route_stores),
            is_cross_county=is_cross,
        )
        route.recalculate_boxes()

        eff_cap = self.effective_capacity.get(vehicle.vehicle_type,
                                              vehicle.capacity)

        if route.total_boxes > eff_cap:
            route.warnings.append(
                f"🔴 超過裝載率限制：{route.total_boxes} 箱 > "
                f"{eff_cap} 箱（{self.load_rate*100:.0f}%）"
            )
        if len(route_stores) < vehicle.target_stores_min:
            route.warnings.append(
                f"⚠️ 門市數偏低：{len(route_stores)} 間 "
                f"（目標 {vehicle.target_stores_min}-{vehicle.target_stores_max}）"
            )
        elif len(route_stores) > vehicle.target_stores_max:
            route.warnings.append(
                f"⚠️ 門市數偏高：{len(route_stores)} 間 "
                f"（目標 {vehicle.target_stores_min}-{vehicle.target_stores_max}）"
            )
        return route

    def _pack_one_route(self, module: int, stores: list) -> tuple:
        """FFD 裝箱：從門市列表打包一條路線"""
        avg_boxes = sum(s.avg_boxes for s in stores) / len(stores) if stores else 5
        cap_5t = self.effective_capacity["5ton"]
        cap_8t = self.effective_capacity["8ton"]
        target_5t_mid = (VEHICLE_SPECS["5ton"]["target_stores_min"] +
                         VEHICLE_SPECS["5ton"]["target_stores_max"]) // 2
        target_8t_mid = (VEHICLE_SPECS["8ton"]["target_stores_min"] +
                         VEHICLE_SPECS["8ton"]["target_stores_max"]) // 2

        # 選擇車型容量
        if avg_boxes * target_5t_mid > cap_5t:
            use_8ton = True
        elif self.pool.available_5ton <= 0:
            use_8ton = True
        elif self.pool.available_8ton <= 0:
            use_8ton = False
        else:
            est_routes_5t = max(1, len(stores) // target_5t_mid)
            use_8ton = est_routes_5t > self.pool.available_5ton

        if use_8ton and self.pool.available_8ton > 0:
            capacity  = cap_8t
            tgt_min   = VEHICLE_SPECS["8ton"]["target_stores_min"]
            tgt_max   = VEHICLE_SPECS["8ton"]["target_stores_max"]
        else:
            capacity  = cap_5t
            tgt_min   = VEHICLE_SPECS["5ton"]["target_stores_min"]
            tgt_max   = VEHICLE_SPECS["5ton"]["target_stores_max"]

        if module == 2:
            tgt_max = min(tgt_max, 15)
            tgt_min = min(tgt_min, 8)

        route_stores, remaining, cur_boxes = [], [], 0
        for store in stores:
            if cur_boxes + store.avg_boxes <= capacity and len(route_stores) < tgt_max:
                route_stores.append(store)
                cur_boxes += store.avg_boxes
            else:
                remaining.append(store)

        # 門市數不足時，嘗試補入小箱數門市
        if len(route_stores) < tgt_min and remaining:
            extra = []
            for store in remaining:
                if cur_boxes + store.avg_boxes <= capacity and len(route_stores) < tgt_max:
                    route_stores.append(store)
                    cur_boxes += store.avg_boxes
                else:
                    extra.append(store)
            remaining = extra

        return route_stores, remaining

    # ---- TSP ----

    def _tsp_optimize(self, stores: list) -> list:
        """Nearest Neighbor + 2-opt"""
        n = len(stores)
        if n <= 2:
            return stores
        dm = self.geocoder.build_distance_matrix(stores)
        seq = self._nearest_neighbor(dm, n)
        seq = self._two_opt(dm, seq, n)
        return [stores[i] for i in seq]

    def _nearest_neighbor(self, dm, n: int) -> list:
        visited = [False] * (n + 1)
        visited[0] = True
        seq, cur = [], 0
        for _ in range(n):
            best, bdist = -1, float('inf')
            for j in range(1, n + 1):
                if not visited[j] and dm[cur][j] < bdist:
                    bdist = dm[cur][j]
                    best = j
            if best == -1:
                break
            visited[best] = True
            seq.append(best - 1)
            cur = best
        return seq

    def _two_opt(self, dm, seq: list, n: int, max_iter: int = 100) -> list:
        if n <= 3:
            return seq
        path = [0] + [s + 1 for s in seq] + [0]
        improved, it = True, 0
        while improved and it < max_iter:
            improved, it = False, it + 1
            for i in range(1, len(path) - 2):
                for j in range(i + 1, len(path) - 1):
                    d1 = dm[path[i-1]][path[i]] + dm[path[j]][path[j+1]]
                    d2 = dm[path[i-1]][path[j]] + dm[path[i]][path[j+1]]
                    if d2 < d1 - 1e-10:
                        path[i:j+1] = path[i:j+1][::-1]
                        improved = True
        return [p - 1 for p in path[1:-1]]

    def _sort_by_arrival_time(self, stores: list) -> list:
        """模組一：依現況到店時間排序"""
        def key(s):
            t = s.current_arrival_time
            if not t or t == "None":
                return 9999
            try:
                return int(t)
            except ValueError:
                return 9999
        return sorted(stores, key=key)

    def _calc_distance(self, stores: list) -> float:
        """計算路線總里程（倉庫→門市...→倉庫）"""
        if not stores:
            return 0
        d = self.geocoder.get_distance_from_warehouse(stores[0])
        for i in range(len(stores) - 1):
            d += self.geocoder.get_distance_km(stores[i], stores[i+1])
        d += self.geocoder.get_distance_from_warehouse(stores[-1])
        return d

    def _dummy_vehicle(self, module: int):
        from models import Vehicle
        return Vehicle(
            vehicle_id="NONE", vehicle_type="none", capacity=0,
            target_stores_min=0, target_stores_max=99, assigned_module=module,
        )
