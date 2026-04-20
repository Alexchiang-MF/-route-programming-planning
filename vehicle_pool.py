"""
主線車輛規劃系統 - 車隊管理
"""
from models import Vehicle
from config import VEHICLE_SPECS


class VehiclePool:
    """管理共用車輛池（5噸車82台 + 8噸車59台）"""

    def __init__(self):
        self.total_5ton = VEHICLE_SPECS["5ton"]["total_count"]
        self.total_8ton = VEHICLE_SPECS["8ton"]["total_count"]
        self.used_5ton = 0
        self.used_8ton = 0
        self.allocated_vehicles = []
        # 按模組追蹤
        self.module_usage = {1: {"5ton": 0, "8ton": 0},
                             2: {"5ton": 0, "8ton": 0},
                             4: {"5ton": 0, "8ton": 0}}
        self._next_id = {"5ton": 1, "8ton": 1}

    @property
    def available_5ton(self):
        return self.total_5ton - self.used_5ton

    @property
    def available_8ton(self):
        return self.total_8ton - self.used_8ton

    def allocate(self, vehicle_type: str, module: int) -> Vehicle:
        """
        分配一台車輛。

        Parameters:
            vehicle_type: "5ton" or "8ton"
            module: 模組編號

        Returns:
            Vehicle 或 None（若無可用車輛）
        """
        if vehicle_type == "5ton":
            if self.available_5ton <= 0:
                return None
            self.used_5ton += 1
            self.module_usage[module]["5ton"] += 1
            vid = f"5T-{self._next_id['5ton']:03d}"
            self._next_id["5ton"] += 1
            spec = VEHICLE_SPECS["5ton"]
        elif vehicle_type == "8ton":
            if self.available_8ton <= 0:
                return None
            self.used_8ton += 1
            self.module_usage[module]["8ton"] += 1
            vid = f"8T-{self._next_id['8ton']:03d}"
            self._next_id["8ton"] += 1
            spec = VEHICLE_SPECS["8ton"]
        else:
            return None

        vehicle = Vehicle(
            vehicle_id=vid,
            vehicle_type=vehicle_type,
            capacity=spec["actual_capacity"],
            target_stores_min=spec["target_stores_min"],
            target_stores_max=spec["target_stores_max"],
            assigned_module=module,
        )
        self.allocated_vehicles.append(vehicle)
        return vehicle

    def choose_vehicle_type(self, total_boxes: int, store_count: int,
                            addresses: list = None) -> str:
        """
        根據條件選擇最佳車型��

        Parameters:
            total_boxes: 預估總箱數
            store_count: 門市數
            addresses: 門市地址列表（用於判斷路況��

        Returns:
            "5ton" or "8ton"
        """
        # 超過5噸車容量，必須用8噸
        if total_boxes > VEHICLE_SPECS["5ton"]["actual_capacity"]:
            if self.available_8ton > 0:
                return "8ton"
            # 8噸車也用完，只能用5噸（會超載，加warning）
            return "5ton"

        # 門市數超過20，偏好8噸
        if store_count > 20 and self.available_8ton > 0:
            return "8ton"

        # 檢查地址關鍵字決定是否適合5噸
        if addresses:
            alley_count = sum(
                1 for addr in addresses
                if any(kw in addr for kw in ["巷", "弄", "山", "產業道��"])
            )
            if alley_count > len(addresses) * 0.3:
                # 超過30%的門市在巷弄/山區，用5噸
                if self.available_5ton > 0:
                    return "5ton"

        # 預設：有5噸用5噸
        if self.available_5ton > 0:
            return "5ton"
        if self.available_8ton > 0:
            return "8ton"

        # 都沒了
        return "5ton"  # 回傳5噸，allocate會回傳None

    def get_summary(self) -> dict:
        """取得車輛使用統計摘要"""
        return {
            "total_5ton": self.total_5ton,
            "total_8ton": self.total_8ton,
            "used_5ton": self.used_5ton,
            "used_8ton": self.used_8ton,
            "available_5ton": self.available_5ton,
            "available_8ton": self.available_8ton,
            "usage_5ton_pct": (self.used_5ton / self.total_5ton * 100) if self.total_5ton else 0,
            "usage_8ton_pct": (self.used_8ton / self.total_8ton * 100) if self.total_8ton else 0,
            "module_usage": dict(self.module_usage),
        }

    def get_resource_status(self, vehicle_type: str) -> str:
        """取得車輛資源狀態"""
        if vehicle_type == "5ton":
            remaining_pct = self.available_5ton / self.total_5ton * 100
        else:
            remaining_pct = self.available_8ton / self.total_8ton * 100

        if remaining_pct > 40:
            return "✅ 剩餘充足"
        elif remaining_pct > 20:
            return "⚠�� 剩餘不足"
        else:
            return "🔴 資源緊張"
