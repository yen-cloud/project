# -*- coding: utf-8 -*-
"""
Created on Tue Mar 11 14:34:43 2025

@author: LiFish
"""
import os
import cv2
from mos_data import get_next_sp_id,is_mosquito_class_exists, insert_mosquito_class
from detect4 import Detection  # 引入新的 Detection 類
import mos_picture 
import time

def process_queue(photo_queue,db):
    search_dict = {}
    device_list = [] 
    list_col = 0 ; add = 0 ; min_num = 0
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
            
            global obj_cou #裁切數量
            # 裁切物件
            obj_cou = detection.crop_objects(
                img_path=file_path,
                results=results,
                save_dir=crop_dir
            )

            print(f"Detection completed for {file_path}")
            os.remove(file_path)  # 處理完成後刪除原始影像
            print(d_id)
            db.insert(f"INSERT INTO `photo` (`photo_id`, `photo_address`, `photo_location`, `photo_time`, `photo_storage`, `device_id`,`msg`,`count`) VALUES ('{photo_id}', '{gps}', '{loc}', '{datetime_str}', '{file_path[:31]}/detected_{os.path.basename(file_path)}', '{d_id}','0',{obj_cou});")
            db.update(f"UPDATE `device` SET `device_address` = '{gps}' WHERE `device`.`device_id` = '{d_id}';")
            sp_id = get_next_sp_id(db)
            time.sleep(3)
            for idx, coord in enumerate(simplified_coordinates):
                class_id = coord["class_id"]
                class_name = coord["class_name"]
                x_min, x_max = coord["x_min"], coord["x_max"]
                y_min, y_max = coord["y_min"], coord["y_max"]
                sp_storage = f"{class_name}_{idx}"
                print(class_id, class_name, x_min, x_max, y_min, y_max)
                
                if not is_mosquito_class_exists(class_id, class_name,db):
                    insert_mosquito_class(class_id, class_name,db)
                    print(class_id, class_name)
                
                db.insert(f"""
                    INSERT INTO `seg_photo` 
                    (`SP_id`, `photo_id`, `mosquito_id`, `SP_storage`, `x1`, `x2`, `y1`, `y2`) 
                    VALUES 
                    ({sp_id}, '{photo_id}', '{class_id}', '{sp_storage}', {x_min}, {x_max}, {y_min}, {y_max});
                """)
               
                sp_id += 1
            print("Seg_photo 表格新增成功")
            
            photo_data = db.select(f"SELECT `photo_id`,`device_id`,`count` FROM `photo` WHERE `photo_id` = '{photo_id}'")
            print("12312312 ",photo_data)
            for i in photo_data:
                dev_name = i[1]
                if dev_name not in search_dict:
                    search_dict.update({dev_name:list_col})  
                    list_col += 1
                    device_list.append([])
                seg_data = db.select(f"SELECT `SP_id`,`mosquito_id`,`x1`,`y1`,`x2`,`y2` FROM `seg_photo` Where `photo_id`= '{i[0]}';")
                print(db.select(f"SELECT `temp` FROM `device` WHERE `device_id` = '{dev_name}';")[0])
                temp_num = int(db.select(f"SELECT `temp` FROM `device` WHERE `device_id` = '{dev_name}';")[0][0])
                search_num = search_dict[dev_name]
                if temp_num == -1: 
                    db.update(f"UPDATE `device` SET `temp` = '{int(i[0])}' WHERE `device_id`='{dev_name}';")
                    device_list[search_num] = []
                    min_num = int(i[0])
                    #print("zero _123")
                else:
                    min_num = temp_num
                    #print(True,min_num)
                    #db.update(f"UPDATE `device` SET `temp` = '{int(i[0])}' WHERE `device_id`='{dev_name}';")
                    
                for j in seg_data:
                    if len(device_list[search_num]) == 0: #temp add here 
                        mos_data = db.select(f"SELECT seg_photo.SP_id, seg_photo.mosquito_id, seg_photo.x1, seg_photo.y1, seg_photo.x2, seg_photo.y2 FROM photo JOIN seg_photo ON photo.photo_id = seg_photo.photo_id WHERE photo.device_id = '{dev_name}' AND seg_photo.new = '1' AND seg_photo.photo_id >= {min_num} ;")
                        
                        #print(f"SELECT seg_photo.SP_id, seg_photo.mosquito_id, seg_photo.x1, seg_photo.y1, seg_photo.x2, seg_photo.y2 FROM photo JOIN seg_photo ON photo.photo_id = seg_photo.photo_id WHERE photo.device_id = '{dev_name}' AND seg_photo.new = '1' AND seg_photo.photo_id >= {min_num} ;")
                        #print(mos_data)
                        if mos_data:
                            for mos in mos_data:
                                device_list[search_num].append(mos)
                        else:
                            device_list[search_num].append(j)
                            db.update(f"UPDATE `seg_photo` SET `new`='1' WHERE `SP_id` = {j[0]};")
                            
                    add = 1
                    for k in device_list[search_num]:  
                        try:
                            pass_id = db.select(f"SELECT `new` FROM `seg_photo` WHERE `SP_id` = {j[0]};")[0][0]
                            if pass_id == 1:
                                break
                        except:
                            pass
                        iou = mos_picture.calculate_iou((k[2],k[3],k[4],k[5]),(j[2],j[3],j[4],j[5]))
                        if 0.8 > iou:
                            pass
                        else:
                            add = 0
                            db.update(f"UPDATE `seg_photo` SET `new`='0' WHERE `SP_id` = {j[0]};")

                    pass_id = db.select(f"SELECT `new` FROM `seg_photo` WHERE `SP_id` = {j[0]};")[0][0]
                    if add and pass_id != 1:
                        device_list[search_num].append(j)
                        #print(device_list[search_num])
                        db.update(f"UPDATE `seg_photo` SET `new`='1' WHERE `SP_id` = {j[0]};")
                
                print("device list: ",device_list[search_num])
        time.sleep(1)