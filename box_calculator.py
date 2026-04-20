"""
主線車輛規劃系統 - 平均箱數計算
"""


def calculate_avg_boxes(daily_boxes: list) -> int:
    """
    計算門市每日固定配送箱數。

    規則：
    - 將所有日期欄位數值加總後取平均值
    - 空值或 0 視為 1 箱（預設最小配送量）
    - 四捨五入至整數
    - 最終結果最小為 1
    """
    if not daily_boxes:
        return 1

    values = []
    for v in daily_boxes:
        if v is None or v == 0 or v == "":
            values.append(1)
        else:
            try:
                val = int(float(v))
                values.append(max(1, val))
            except (ValueError, TypeError):
                values.append(1)

    if not values:
        return 1

    avg = sum(values) / len(values)
    return max(1, round(avg))
