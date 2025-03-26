# -*- coding: utf-8 -*-
"""
Created on Tue Mar 11 14:34:43 2025

@author: LiFish
"""
import os
import cv2
from mos_data import get_next_sp_id, is_mosquito_class_exists, insert_mosquito_class
from detect4 import Detection  # 引入新的 Detection 類
import mos_picture 
import time

def process_queue(photo_queue, db):
    search_dict = {}
    device_list = [] 
    list_col = 0
    add = 0
    min_num = 0
    detection = Detection(weights='v11best.pt', device='cuda:0')
    detection.load_model()  # 載入模型
    while True:
        if not photo_queue.empty():
            task = photo_queue.get()
            file_path = task['file_path']
            save_dir = task['save_dir']
            photo_id = task['id']
            gps = task['gps']
            loc = task['loc']
            d_id = task['device_id']
            d_name = task['device_name']
            datetime_str = task['datetime']
            print(task)
            crop_dir = os.path.join(save_dir, 'crop')
            
            print(f"Processing {file_path}")
            os.makedirs(crop_dir, exist_ok=True)

            # 讀取原圖
            original_img = cv2.imread(file_path)
            if original_img is None:
                print(f"Failed to read image: {file_path}")
                continue

            # 儲存原圖到同一資料夾
            original_save_path = os.path.join(save_dir, "original.jpg")
            cv2.imwrite(original_save_path, original_img)

            # 執行 YOLO 預測
            results = detection.predict(img_path=file_path, conf=0.5)

            # 標註影像
            simplified_coordinates = detection.annotate_image(
                img_path=file_path,
                results=results,
                save_path=os.path.join(save_dir, f"detected_{os.path.basename(file_path)}")
            )[2]
            
            global obj_cou  # 裁切數量
            # 裁切物件
            obj_cou = detection.crop_objects(
                img_path=file_path,
                results=results,
                save_dir=crop_dir
            )

            print(f"Detection completed for {file_path}")
            os.remove(file_path)  # 處理完成後刪除原始影像
            print(d_id)
            
            if gps == "None":
                gps_result = db.select("SELECT device_address FROM device WHERE device_id = ?", (d_id,))
                gps = gps_result[0][0] if gps_result else None
                print("in =>", gps)
            print(gps)

            # 插入 photo 表記錄（包含 count 和 processed 欄位，processed 初始為 0）
            db.insert(
                "INSERT INTO photo (photo_id, photo_address, photo_location, photo_time, photo_storage, device_id, msg, count, processed) VALUES (?, ?, ?, ?, ?, ?, '0', ?, 0);",
                (photo_id, gps, loc, datetime_str, f"{file_path[:31]}/detected_{os.path.basename(file_path)}", d_id, obj_cou)
            )
            db.update("UPDATE device SET device_address = ? WHERE device_id = ?;", (gps, d_id))

            sp_id = get_next_sp_id(db)
            time.sleep(3)
            for idx, coord in enumerate(simplified_coordinates):
                class_id = coord["class_id"]
                class_name = coord["class_name"]
                x_min, x_max = coord["x_min"], coord["x_max"]
                y_min, y_max = coord["y_min"], coord["y_max"]
                sp_storage = f"{class_name}_{idx}"
                print(class_id, class_name, x_min, x_max, y_min, y_max)
                
                if not is_mosquito_class_exists(class_id, class_name, db):
                    insert_mosquito_class(class_id, class_name, db)
                    print(class_id, class_name)
                
                # 插入 seg_photo 記錄
                db.insert(
                    "INSERT INTO seg_photo (SP_id, photo_id, mosquito_id, SP_storage, x1, x2, y1, y2) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                    (sp_id, photo_id, class_id, sp_storage, x_min, x_max, y_min, y_max)
                )
                sp_id += 1
            print("Seg_photo 表格新增成功")

            # 更新 photo 表的 processed 欄位為 1，表示處理完成
            db.update(
                "UPDATE photo SET processed = 1 WHERE photo_id = ?;",
                (photo_id,)
            )

            # 以下是原有的邏輯，處理 device_list 和 new 標記
            photo_data = db.select("SELECT photo_id, device_id, count FROM photo WHERE photo_id = ?;", (photo_id,))
            print("12312312 ", photo_data)
            for i in photo_data:
                dev_name = i[1]  # device_id
                if dev_name not in search_dict:
                    search_dict.update({dev_name: list_col})  
                    list_col += 1
                    device_list.append([])
                seg_data = db.select("SELECT SP_id, mosquito_id, x1, y1, x2, y2 FROM seg_photo WHERE photo_id = ?;", (i[0],))
                temp_result = db.select("SELECT temp FROM device WHERE device_id = ?;", (dev_name,))
                temp_num = int(temp_result[0][0]) if temp_result else -1
                search_num = search_dict[dev_name]
                if temp_num == -1: 
                    db.update("UPDATE device SET temp = ? WHERE device_id = ?;", (int(i[0]), dev_name))
                    device_list[search_num] = []
                    min_num = int(i[0])
                else:
                    min_num = temp_num
                    
                for j in seg_data:
                    if len(device_list[search_num]) == 0:  # temp add here 
                        mos_data = db.select(
                            "SELECT seg_photo.SP_id, seg_photo.mosquito_id, seg_photo.x1, seg_photo.y1, seg_photo.x2, seg_photo.y2 "
                            "FROM photo JOIN seg_photo ON photo.photo_id = seg_photo.photo_id "
                            "WHERE photo.device_id = ? AND seg_photo.new = '1' AND seg_photo.photo_id >= ?;",
                            (dev_name, min_num)
                        )
                        if mos_data:
                            for mos in mos_data:
                                device_list[search_num].append(mos)
                        else:
                            device_list[search_num].append(j)
                            db.update("UPDATE seg_photo SET new = '1' WHERE SP_id = ?;", (j[0],))
                            
                    add = 1
                    for k in device_list[search_num]:  
                        try:
                            pass_id = db.select("SELECT new FROM seg_photo WHERE SP_id = ?;", (j[0],))[0][0]
                            if pass_id == 1:
                                break
                        except:
                            pass
                        iou = mos_picture.calculate_iou((k[2], k[3], k[4], k[5]), (j[2], j[3], j[4], j[5]))
                        if 0.8 > iou:
                            pass
                        else:
                            add = 0
                            db.update("UPDATE seg_photo SET new = '0' WHERE SP_id = ?;", (j[0],))

                    pass_id = db.select("SELECT new FROM seg_photo WHERE SP_id = ?;", (j[0],))[0][0]
                    if add and pass_id != 1:
                        device_list[search_num].append(j)
                        db.update("UPDATE seg_photo SET new = '1' WHERE SP_id = ?;", (j[0],))
                
                print("device list: ", device_list[search_num])
        time.sleep(1)