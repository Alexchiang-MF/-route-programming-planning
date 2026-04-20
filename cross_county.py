"""
主線車輛規劃系統 - 跨縣市整併邏輯（僅模組四）
"""
from config import (
    CROSS_COUNTY_RULES,
    MERGE_MILEAGE_REDUCTION_THRESHOLD,
    MERGE_TIME_SAVINGS_THRESHOLD,
    VEHICLE_SPECS,
)


class CrossCountyConsolidator:
    """模組四跨縣市整併評估器"""

    def __init__(self, geocoder):
        self.geocoder = geocoder

    def find_eligible_stores(self, stores_by_county: dict) -> list:
        """
        找出符合跨縣市整併條件的門市群組。

        Parameters:
            stores_by_county: {county: [Store, ...]}

        Returns:
            list of merge candidates:
            [{"county_a": str, "county_b": str, "stores_a": [...], "stores_b": [...],
              "rule": dict}, ...]
        """
        candidates = []

        for rule in CROSS_COUNTY_RULES:
            county_a = rule["county_a"]
            county_b = rule["county_b"]

            if county_a not in stores_by_county or county_b not in stores_by_county:
                continue

            # 篩選符合行政區條件的門市
            stores_a = self._filter_by_districts(
                stores_by_county[county_a], rule.get("districts_a")
            )
            stores_b = self._filter_by_districts(
                stores_by_county[county_b], rule.get("districts_b")
            )

            if not stores_a or not stores_b:
                continue

            candidates.append({
                "county_a": county_a,
                "county_b": county_b,
                "stores_a": stores_a,
                "stores_b": stores_b,
                "rule": rule,
            })

        return candidates

    def _filter_by_districts(self, stores: list, districts: list) -> list:
        """根據行政區列表篩選門市（None表示全部符合）"""
        if districts is None:
            return stores
        return [s for s in stores if s.district in districts]

    def evaluate_merge(self, candidate: dict) -> dict:
        """
        評估一個跨縣市整併候選的效益。

        Returns:
            {
                "viable": bool,
                "mileage_before": float,
                "mileage_after": float,
                "mileage_reduction": float,
                "mileage_reduction_pct": float,
                "merged_stores": list,
                "reason": str,
            }
        """
        stores_a = candidate["stores_a"]
        stores_b = candidate["stores_b"]

        # 計算整併前的總距離（各自從倉庫出發的估算）
        dist_a = self._estimate_group_distance(stores_a)
        dist_b = self._estimate_group_distance(stores_b)
        mileage_before = dist_a + dist_b

        # 計算整併後的總距離
        merged = stores_a + stores_b
        mileage_after = self._estimate_group_distance(merged)

        reduction = mileage_before - mileage_after
        reduction_pct = reduction / mileage_before if mileage_before > 0 else 0

        # 判斷是否值得整併
        viable = (
            reduction_pct >= MERGE_MILEAGE_REDUCTION_THRESHOLD or
            reduction / 35 >= MERGE_TIME_SAVINGS_THRESHOLD  # 用市區速度粗估時間節省
        )

        # 額外檢查：整併後的總箱數是否能合理分配
        total_boxes = sum(s.avg_boxes for s in merged)
        max_capacity = VEHICLE_SPECS["8ton"]["actual_capacity"]
        if total_boxes > max_capacity * 5:  # 如果需要超過5台車，可能不適合整併
            # 仍可整併，但分配到多台車
            pass

        reason = ""
        if viable:
            reason = (f"整併 {candidate['county_a']} + {candidate['county_b']}，"
                      f"預估減少里程 {reduction:.1f} km ({reduction_pct:.0%})")
        else:
            reason = (f"{candidate['county_a']} + {candidate['county_b']} "
                      f"整併效益不足 (減少 {reduction_pct:.0%})")

        return {
            "viable": viable,
            "mileage_before": mileage_before,
            "mileage_after": mileage_after,
            "mileage_reduction": reduction,
            "mileage_reduction_pct": reduction_pct,
            "merged_stores": merged if viable else [],
            "reason": reason,
        }

    def _estimate_group_distance(self, stores: list) -> float:
        """粗略估算一群門市的配送總距離（用平均到倉庫距離×2）"""
        if not stores:
            return 0
        total = 0
        for s in stores:
            total += self.geocoder.get_distance_from_warehouse(s)
        # 往返距離 + 門市間距離（約估為平均倉庫距離的 0.3 倍）
        avg_dist = total / len(stores)
        return avg_dist * 2 + avg_dist * 0.3 * len(stores) / 20

    def execute_merges(self, stores_by_county: dict) -> tuple:
        """
        執行跨縣市整併，回傳更新後的分組和整併報告。

        Parameters:
            stores_by_county: {county: [Store, ...]}

        Returns:
            (updated_groups: dict, merge_reports: list)
            updated_groups: {group_key: [Store, ...]}
            merge_reports: [{"county_a": ..., "county_b": ..., "reason": ..., ...}]
        """
        candidates = self.find_eligible_stores(stores_by_county)
        merge_reports = []
        merged_store_ids = set()
        updated_groups = {}

        for candidate in candidates:
            # 排除已被其他整併使用的門市
            candidate["stores_a"] = [
                s for s in candidate["stores_a"]
                if s.store_id not in merged_store_ids
            ]
            candidate["stores_b"] = [
                s for s in candidate["stores_b"]
                if s.store_id not in merged_store_ids
            ]
            if not candidate["stores_a"] or not candidate["stores_b"]:
                continue

            result = self.evaluate_merge(candidate)
            merge_reports.append({
                "county_a": candidate["county_a"],
                "county_b": candidate["county_b"],
                "description": candidate["rule"]["description"],
                **result,
            })

            if result["viable"]:
                # 標記已整併的門市（避免重複分配）
                group_key = f"{candidate['county_a']}+{candidate['county_b']}"
                merged_stores = result["merged_stores"]
                for s in merged_stores:
                    merged_store_ids.add(s.store_id)
                updated_groups[group_key] = merged_stores

        # 將未整併的門市保留原分組
        for county, stores in stores_by_county.items():
            remaining = [s for s in stores if s.store_id not in merged_store_ids]
            if remaining:
                updated_groups[f"{county}"] = remaining

        return updated_groups, merge_reports
