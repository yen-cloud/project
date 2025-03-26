# -*- coding: utf-8 -*-
"""
Created on Tue Mar 11 14:26:32 2025

@author: LiFish
"""
import os
import pandas as pd
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # 設定 Matplotlib 使用無 GUI 的後端
import matplotlib.pyplot as plt

def get_unsent_photo(db):
    sql = """
        SELECT p.photo_id, p.photo_storage, u.device_id
        FROM photo AS p
        JOIN user AS u ON p.device_id = u.device_id
        WHERE p.msg = '0' AND p.processed = 1;
    """
    result = db.select(sql)
    print("查詢未發送照片結果:", result)
    if result:
        return result[0]
    return None

def get_next_sp_id(db):
    """
    從 seg_photo 中取得當前最大的 SP_id，並計算下一個可用的 SP_id。
    如果資料表為空，則返回 1。
    """
    # 修改：移除反引號
    result = db.select("SELECT MAX(SP_id) FROM seg_photo;")[0][0]
    return result + 1 if result else 1

def is_mosquito_class_exists(class_id, class_name, db):
    """
    檢查 mosquito 資料表中是否存在指定的 class_id 和 class_name。
    """
    # 修改：使用參數化查詢，移除反引號，改用 ?
    query = """
        SELECT COUNT(*) FROM mosquito 
        WHERE mosquito_id = ? AND mosquito_name = ?;
    """
    result = db.select(query, (class_id, class_name))[0][0]
    return result > 0  # 如果查詢結果大於 0，表示 class 已存在

def insert_mosquito_class(class_id, class_name, db):
    """
    如果 class_id 和 class_name 不存在於資料表，新增到 mosquito 資料表中。
    """
    # 修改：使用參數化查詢，移除反引號，改用 ?
    db.insert(
        "INSERT INTO mosquito (mosquito_id, mosquito_name) VALUES (?, ?);",
        (class_id, class_name)
    )
    print(f"新增到 mosquito 資料表: mosquito_id={class_id}, mosquito_name={class_name}")

def generate_last_7days_chart(d_id, db):
    """
    根據 photo 與 seg_photo 資料計算最近 7 天的蚊子數量，並保存圖表。
    如果沒有資料，生成空白圖表，X 軸和 Y 軸與有資料時一致。
    """
    # 檢查資料庫連線
    if db is None:
        print("Database connection is not initialized.")
        return None

    # 創建 history 資料夾
    history_folder = "history"
    os.makedirs(history_folder, exist_ok=True)

    # 查詢裝置名稱
    try:
        device_name_query = db.select("SELECT device_name FROM device WHERE device_id = ?", (d_id,))
        if not device_name_query:
            print(f"No device found for device_id: {d_id}")
            return None
        device_name = device_name_query[0][0]
    except Exception as e:
        print(f"Failed to query device name: {e}")
        return None

    # 查詢 photo 資料
    try:
        photo_data = db.select("""
            SELECT photo_id, photo_time 
            FROM photo 
            WHERE device_id = ?
            ORDER BY photo_id ASC;
        """, (d_id,))
    except Exception as e:
        print(f"Failed to query photo data: {e}")
        return None

    # 查詢蚊子名稱
    try:
        mosquito_data = db.select("SELECT mosquito_id, mosquito_name FROM mosquito;")
    except Exception as e:
        print(f"Failed to query mosquito data: {e}")
        return None

    # 查詢 seg_photo，區分 new=0 和 new!=0 的記錄
    try:
        seg_photo_data = db.select("SELECT photo_id, mosquito_id, new FROM seg_photo;")
    except Exception as e:
        print(f"Failed to query seg_photo data: {e}")
        return None

    # 計算最近 7 天範圍
    now = datetime.now()
    last_7days = now - timedelta(days=7)

    # 處理蚊子名稱
    if not mosquito_data:
        mosquito_names = ["No Mosquito"]
    else:
        mosquito_df = pd.DataFrame(mosquito_data, columns=["mosquito_id", "mosquito_name"])
        mosquito_names = mosquito_df["mosquito_name"].tolist()

    # 如果沒有資料，生成空白圖表
    if not photo_data or not seg_photo_data:
        # 模擬空白資料，X 軸分為 7 個點（每天一個點）
        time_labels = pd.date_range(start=last_7days, end=now, freq='D').strftime("%m/%d %H:%M")
        plt.figure(figsize=(12, 8))
        for mosquito in mosquito_names:
            plt.plot(time_labels, [0] * len(time_labels), marker="o", label=mosquito)
        plt.xticks(fontsize=10)
        plt.xlabel("Time (MM/DD HH:MM)")
        plt.ylabel("Count")
        plt.ylim(0, 5)  # 設置 Y 軸範圍為 0 到 5（整數）
        plt.yticks(range(0, 6, 1))  # 設置 Y 軸刻度為整數（0, 1, 2, 3, 4, 5）
        plt.title(f"{device_name} Mosquito Count History (Last 7 days)")
        plt.legend()
        plt.tight_layout()
        today_date = now.strftime("%Y-%m-%d")
        chart_path = os.path.join(history_folder, f"{device_name}_{today_date}_7days_mosquito_history.png")
        plt.savefig(chart_path)
        plt.close()
        return chart_path

    # 轉換為 DataFrame
    photo_df = pd.DataFrame(photo_data, columns=["photo_id", "photo_time"])
    seg_photo_df = pd.DataFrame(seg_photo_data, columns=["photo_id", "mosquito_id", "new"])

    # 確保 photo_time 是 datetime 格式
    try:
        photo_df["photo_time"] = pd.to_datetime(photo_df["photo_time"], format="%Y%m%d%H%M%S")
    except Exception as e:
        print(f"Failed to parse photo_time: {e}")
        return None

    # 統一 photo_id 類型為 int64
    try:
        photo_df["photo_id"] = pd.to_numeric(photo_df["photo_id"], errors='coerce')
        seg_photo_df["photo_id"] = pd.to_numeric(seg_photo_df["photo_id"], errors='coerce')
    except Exception as e:
        print(f"Failed to convert photo_id to numeric: {e}")
        return None

    # 保留所有 photo_id，確保 new=0 也納入
    filtered_seg_photo = seg_photo_df[seg_photo_df["new"] != 0]
    merged_df = photo_df.merge(filtered_seg_photo, on="photo_id", how="left")

    # 如果某個 photo_id 完全沒有 new!=0 的紀錄，仍然要保留
    merged_df.fillna({"mosquito_id": -1}, inplace=True)  # -1 代表沒有蚊子
    merged_df = merged_df.sort_values(by="photo_time")

    # 合併蚊子名稱
    merged_df = merged_df.merge(mosquito_df, on="mosquito_id", how="left")
    merged_df["mosquito_name"].fillna("No Mosquito", inplace=True)  # 沒有蚊子的情況

    # 只保留最近 7 天的資料
    merged_df = merged_df[merged_df["photo_time"] >= last_7days]

    # 如果最近 7 天內沒有資料，生成空白圖表
    if merged_df.empty:
        # 模擬空白資料，X 軸分為 7 個點（每天一個點）
        time_labels = pd.date_range(start=last_7days, end=now, freq='D').strftime("%m/%d %H:%M")
        plt.figure(figsize=(12, 8))
        for mosquito in mosquito_names:
            plt.plot(time_labels, [0] * len(time_labels), marker="o", label=mosquito)
        plt.xticks(fontsize=10)
        plt.xlabel("Time (MM/DD HH:MM)")
        plt.ylabel("Count")
        plt.ylim(0, 5)  # 設置 Y 軸範圍為 0 到 5（整數）
        plt.yticks(range(0, 6, 1))  # 設置 Y 軸刻度為整數（0, 1, 2, 3, 4, 5）
        plt.title(f"{device_name} Mosquito Count History (Last 7 days)")
        plt.legend()
        plt.tight_layout()
        today_date = now.strftime("%Y-%m-%d")
        chart_path = os.path.join(history_folder, f"{device_name}_{today_date}_7days_mosquito_history.png")
        plt.savefig(chart_path)
        plt.close()
        return chart_path

    # 確保所有蚊子種類都出現在結果中
    grouped = merged_df.groupby(["photo_time", "mosquito_name"]).size().unstack(fill_value=0)
    
    for mosquito in mosquito_names:
        if mosquito not in grouped.columns:
            grouped[mosquito] = 0

    # 繪製圖表
    plt.figure(figsize=(12, 8))
    for mosquito in mosquito_names:
        plt.plot(grouped.index.strftime("%m/%d %H:%M"), grouped[mosquito], marker="o", label=mosquito)

    # 設置 Y 軸刻度以最大值為基準
    max_count = int(grouped.max().max())  # 找到最大計數（整數）
    if max_count == 1:
        plt.ylim(0, 1)  # 如果最大值為 1，Y 軸範圍為 0 到 1
        plt.yticks([0, 1])  # 刻度為 [0, 1]
    else:
        plt.ylim(0, max_count)  # Y 軸範圍為 0 到最大值
        plt.yticks(range(0, max_count + 1, 1))  # 刻度為 [0, 1, 2, ..., max_count]

    plt.xticks(fontsize=10)
    plt.xlabel("Time (MM/DD HH:MM)")
    plt.ylabel("Count")
    plt.title(f"{device_name} Mosquito Count History (Last 7 days)")
    plt.legend()
    plt.tight_layout()

    # 生成檔案名稱
    today_date = now.strftime("%Y-%m-%d")
    chart_path = os.path.join(history_folder, f"{device_name}_{today_date}_7days_mosquito_history.png")

    # 儲存圖表
    plt.savefig(chart_path)
    plt.close()

    return chart_path