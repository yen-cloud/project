# -*- coding: utf-8 -*-
"""
Created on Tue Mar 11 14:14:20 2025

@author: LiFish
"""

def calculate_iou(rect1, rect2):
    # 獲取矩形邊界
    x1_1, y1_1, x2_1, y2_1 = rect1
    x1_2, y1_2, x2_2, y2_2 = rect2

    # 計算交集邊界
    ix1 = max(x1_1, x1_2)
    iy1 = max(y1_1, y1_2)
    ix2 = min(x2_1, x2_2)
    iy2 = min(y2_1, y2_2)

    # 計算交集面積
    intersection_area = 0
    if ix1 < ix2 and iy1 < iy2:
        intersection_area = (ix2 - ix1) * (iy2 - iy1)

    # 計算兩個矩形的面積
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)

    # 計算聯集面積
    union_area = area1 + area2 - intersection_area

    # 計算 IoU
    iou = intersection_area / union_area if union_area > 0 else 0
    return iou