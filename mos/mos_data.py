# -*- coding: utf-8 -*-
"""
Created on Tue Mar 11 14:26:32 2025

@author: LiFish
"""
import os
import pandas as pd
from datetime import datetime , timedelta
import matplotlib
matplotlib.use('Agg')  # 設定 Matplotlib 使用無 GUI 的後端
import matplotlib.pyplot as plt

def get_unsent_photo(db):
    #查詢資料庫中 msg = 0 的照片記錄，並通過 JOIN 獲取 device_id。
    sql = """
        SELECT p.photo_id, p.photo_storage, u.device_id
        FROM photo AS p
        JOIN user AS u ON p.device_id = u.device_id
        WHERE p.msg = '0';
    """
    result = db.select(sql)
    print("查詢未發送照片結果:", result)
    db.commit()
    if result:
        return result[0]  # 回傳第一筆結果 (photo_id, photo_storage, device_id)
    return None

def get_next_sp_id(db):
    """
    從 seg_photo 中取得當前最大的 SP_id，並計算下一個可用的 SP_id。
    如果資料表為空，則返回 1。
    """
    result = db.select("SELECT MAX(SP_id) FROM `seg_photo`;")[0][0]
    return result + 1 if result else 1

def is_mosquito_class_exists(class_id, class_name,db): #判斷蚊子種類是否在mosquito資料表中
    """
    檢查 mosquito 資料表中是否存在指定的 class_id 和 class_name。
    """
    query = f"""
        SELECT COUNT(*) FROM `mosquito` 
        WHERE mosquito_id = '{class_id}' AND mosquito_name = '{class_name}';
    """
    result = db.select(query)[0][0]
    return result > 0  # 如果查詢結果大於 0，表示 class 已存在

def insert_mosquito_class(class_id, class_name, db):  #新增蚊子種類到mosquito資料表中
    """
    如果 class_id 和 class_name 不存在於資料表，新增到 mosquito 資料表中。
    """
    db.insert(f"""
        INSERT INTO `mosquito` (`mosquito_id`, `mosquito_name`) 
        VALUES ('{class_id}', '{class_name}');
    """)
    print(f"新增到 mosquito 資料表: mosquito_id={class_id}, mosquito_name={class_name}")

def generate_last_7days_chart(d_id,db):
    """
    根據 photo 與 seg_photo 資料計算最近 7 天的蚊子數量，並保存圖表。
    """
    # 創建 history 資夾
    history_folder = "history"
    os.makedirs(history_folder, exist_ok=True)

    # 查詢裝置名稱
    device_name = db.select(f"SELECT `device_name` FROM `device` WHERE `device_id`='{d_id}' ")[0][0]

    # 查詢 photo 資料
    photo_data = db.select(f"""
        SELECT photo_id, photo_time 
        FROM photo 
        WHERE device_id = '{d_id}'
        ORDER BY CAST(photo_id AS UNSIGNED) ASC;
    """)

    # 查詢蚊子名稱
    mosquito_data = db.select("SELECT mosquito_id, mosquito_name FROM mosquito;")

    # 查詢 seg_photo，區分 new=0 和 new!=0 的記錄
    seg_photo_data = db.select("SELECT photo_id, mosquito_id, new FROM seg_photo;")

    if not photo_data or not mosquito_data or not seg_photo_data:
        print("未從資料庫中獲取到足夠資料。")
        return None

    # 轉換為 DataFrame
    photo_df = pd.DataFrame(photo_data, columns=["photo_id", "photo_time"])
    mosquito_df = pd.DataFrame(mosquito_data, columns=["mosquito_id", "mosquito_name"])
    seg_photo_df = pd.DataFrame(seg_photo_data, columns=["photo_id", "mosquito_id", "new"])

    # 確保 photo_time 是 datetime 格式
    photo_df["photo_time"] = pd.to_datetime(photo_df["photo_time"], format="%Y%m%d%H%M%S")

    # 計算最近 7 天範圍
    now = datetime.now()
    last_7days = now - timedelta(days=7)

    # 保留所有 photo_id，確保 new=0 也納入
    filtered_seg_photo = seg_photo_df[seg_photo_df["new"] != 0]  # 只保留 new != 0 待處理
    merged_df = photo_df.merge(filtered_seg_photo, on="photo_id", how="left")

    # 如果某個 photo_id 完全沒有 new!=0 的紀錄，仍然要保留
    merged_df.fillna({"mosquito_id": -1}, inplace=True)  # -1 代表沒有蚊子
    merged_df = merged_df.sort_values(by="photo_time")

    # 合併蚊子名稱
    merged_df = merged_df.merge(mosquito_df, on="mosquito_id", how="left")
    merged_df["mosquito_name"].fillna("No Mosquito", inplace=True)  # 沒有蚊子的情況

    # 只保留最近 7 天的資料
    merged_df = merged_df[merged_df["photo_time"] >= last_7days]

    # 確保所有蚊子種類都出現在結果中
    mosquito_names = mosquito_df["mosquito_name"].tolist()
    grouped = merged_df.groupby(["photo_time", "mosquito_name"]).size().unstack(fill_value=0)
    
    for mosquito in mosquito_names:
        if mosquito not in grouped.columns:
            grouped[mosquito] = 0

    # 繪製圖表
    plt.figure(figsize=(12, 8))
    for mosquito in mosquito_names:
        plt.plot(grouped.index.strftime("%m/%d %H:%M"), grouped[mosquito], marker="o", label=mosquito)

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