"""
主線車輛規劃系統 - 資料模型
"""
from dataclasses import dataclass, field


@dataclass
class Store:
    """門市資料"""
    store_id: str
    store_name: str
    county: str
    district: str
    address: str
    current_route: str
    current_arrival_time: str
    daily_boxes: list  # 7天原始資料
    avg_boxes: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    module: int = 0

    def __repr__(self):
        return f"Store({self.store_id}, {self.store_name}, {self.county}, avg={self.avg_boxes}箱)"


@dataclass
class Vehicle:
    """車輛"""
    vehicle_id: str       # e.g., "5T-001", "8T-042"
    vehicle_type: str     # "5ton" or "8ton"
    capacity: int         # 144 or 216
    target_stores_min: int
    target_stores_max: int
    assigned_module: int = 0

    @property
    def type_name(self):
        return "5噸車" if self.vehicle_type == "5ton" else "8噸車"

    def __repr__(self):
        return f"Vehicle({self.vehicle_id}, {self.type_name}, cap={self.capacity})"


@dataclass
class Route:
    """配送路線"""
    route_id: str
    vehicle: Vehicle
    module: int
    stores: list = field(default_factory=list)
    total_boxes: int = 0
    estimated_distance_km: float = 0.0
    estimated_time_hours: float = 0.0
    counties_visited: set = field(default_factory=set)
    is_cross_county: bool = False
    warnings: list = field(default_factory=list)

    @property
    def store_count(self):
        return len(self.stores)

    @property
    def capacity_ratio(self):
        if self.vehicle.capacity == 0:
            return 0
        return self.total_boxes / self.vehicle.capacity

    @property
    def status_icon(self):
        """根據約束狀態回傳圖示"""
        if self.total_boxes > self.vehicle.capacity:
            return "🔴"
        if self.warnings:
            return "⚠️"
        return "✅"

    def recalculate_boxes(self):
        """重新計算總箱數"""
        self.total_boxes = sum(s.avg_boxes for s in self.stores)
        self.counties_visited = set(s.county for s in self.stores)

    def __repr__(self):
        return (f"Route({self.route_id}, {self.vehicle.type_name}, "
                f"{self.store_count}店, {self.total_boxes}箱)")
