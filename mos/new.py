from flask import Flask, request, jsonify, send_from_directory, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError ,LineBotApiError
from linebot.models import MessageEvent, TextSendMessage, RichMenu, RichMenuArea, RichMenuSize, RichMenuBounds, MessageAction, ImageSendMessage
from werkzeug.utils import secure_filename
from SQL import Database
import logging
import pymysql
import os
import time
import threading
from datetime import datetime
import queue
import sys
import re
from mos_data import generate_last_7days_chart, get_unsent_photo
from process import process_queue  

# 設置照片隊列
photo_queue = queue.Queue()
sys.setrecursionlimit(3000)  # 將遞迴深度增加

# 基本參數設定
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
UPLOAD_FOLDER = 'uploads'
PHOTO_FOLDER = 'uploads'
BASE_URL = "https://800b-220-128-241-245.ngrok-free.app/"
line_bot_api = LineBotApi('6aM53Z8MDsBADtBFHV6ZtpWBGyB9WdZHDhYwQeyBpPOGcmM9kEhpFDOqcdPg0pr7sp6YSJSRtXQNAnNgfw66XB7R0xYapQfU6IynCAThkTa6oJuQjcdtp5zIYPtcWBPnmRwYDDvs21opy/7hUD93dwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('a05ae0870e7a1e96463b33e5a8e203b5')

# 檢查並創建目錄
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PHOTO_FOLDER):
    os.makedirs(PHOTO_FOLDER)
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = Database('127.0.0.1', 3306, 'root', '', 'mosquito') #SQL setting

def create_rich_menu():
    # 同样的创建 Rich Menu 的代码
    button1 = RichMenuArea(
        bounds=RichMenuBounds(x=0, y=843, width=833, height=843),
        action=MessageAction(label='新增裝置', text='新增裝置綁定')
    )
    
    button2 = RichMenuArea(
        bounds=RichMenuBounds(x=833, y=843, width=833, height=843), 
        action=MessageAction(label='拍照間隔時間', text='調整拍照間隔時間')
    )
    
    button3 = RichMenuArea(
        bounds=RichMenuBounds(x=1666, y=843, width=834, height=843), 
        action=MessageAction(label='重置', text='重置裝置')
    )

    button4 = RichMenuArea(
        bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
        action=MessageAction(label='網頁查詢', text='查詢裝置網頁')
        
    )

    button5 = RichMenuArea(
        bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
        action=MessageAction(label='拍照', text='裝置拍照')       
    )

    button6 = RichMenuArea(
        bounds=RichMenuBounds(x=1686, y=0, width=833, height=843),
        action=MessageAction(label='歷史紀錄', text='查詢裝置歷史紀錄')
    )

    rich_menu = RichMenu(
        size=RichMenuSize(width=2500, height=1686),
        selected=True,
        name='function',
        chat_bar_text='功能選單',
        areas=[button1, button2, button3, button4, button5, button6]
    )

    try:
        # Create the Rich Menu
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu)
        print(f'Rich Menu created. rich_menu_id: {rich_menu_id}')
        
        # Upload the Rich Menu image
        with open('查詢資料.png', 'rb') as f:
            line_bot_api.set_rich_menu_image(rich_menu_id, 'image/png', f)
            print('Rich Menu image uploaded.')

        # Set the Rich Menu as the default
        line_bot_api.set_default_rich_menu(rich_menu_id)
        print('Rich Menu set as default.')
        
    except Exception as e:
        print(f'Error creating Rich Menu: {e}')


@app.route('/test', methods=['POST'])
def test1():
    return jsonify({'msg':123})

@app.route('/upload', methods=['POST'])
def upload_photo():
    datetime_str = request.form.get('datetime')
    device_name = request.form.get('device_name')
    gps = request.form.get('gps')
    loc = request.form.get('loc')
    d_id = request.form.get('device_id')

    if not datetime_str or not device_name or not gps:
        return jsonify({"error": "Missing required fields: datetime, device_name, or gps"}), 400
    try:
        datetime_obj = datetime.strptime(datetime_str, "%Y%m%d%H%M%S")
    except ValueError:
        return jsonify({"error": "Invalid datetime format. Expected YYYYMMDDHHMMSS."}), 400

    if 'image' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        save_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"{device_name}/{datetime_str}")
        os.makedirs(save_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        file_path = os.path.join(save_dir, filename)
        file.save(file_path)
        photo_id = db.select("SELECT count(*) as `photo_id` FROM photo;")[0][0]
        print('photo_id',photo_id)
        photo_queue.put({
            'file_path': file_path,
            'save_dir': save_dir,
            'gps': gps,
            'datetime': datetime_str,
            'device_name': device_name,
            'loc':loc,
            'id':photo_id,
            'device_id':d_id
        })
            
        return jsonify({"success": "Photo uploaded successfully and added to queue."}), 200
        
@app.route('/take', methods=['POST'])
def take_pic():
    d_id = request.form.get('device_id')
    result = db.select(f"SELECT `take_photo` FROM `device` WHERE `device_id` = '{d_id}';")   
    if result:
        db.update(f"UPDATE `device` SET `take_photo` = '0' WHERE `device`.`device_id` = '{d_id}';")
        db.update(f"UPDATE `device` SET `photo_take`='1' WHERE `device`.`device_id` = '{d_id}';")       
        return jsonify({"message": f"{result[0][0]}"}), 200

    return jsonify({"error": "Failed to fetch data"}), 500

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@app.route('/uploads/<path:filepath>')
def serve_pics(filepath):
    print(filepath)
    return send_from_directory('./uploads', filepath)

def monitor_and_send_photos():
    """
    輪詢資料庫，尋找未發送的照片，並傳送給與照片關聯的使用者。
    """
    while True:
        try:
            # 確保資料庫連線存活
            db.reconnect()

            # 從資料庫獲取未發送的照片記錄
            photo_record = get_unsent_photo(db)
            if photo_record:
                photo_id, photo_storage, device_id = photo_record
                logging.info(f"Processing photo_id: {photo_id}, device_id: {device_id}")

                # 通過 device_id 查找所有綁定的 user_line
                sql_user_line = "SELECT user_line FROM user WHERE device_id = %s;"
                user_result = db.select(sql_user_line, (device_id,))
                sql_devicename ="SELECT device_name FROM device WHERE device_id = %s;"
                devicename_result = db.select(sql_devicename, (device_id,))
                devicename = devicename_result[0][0]
                if not user_result:
                    logging.warning(f"找不到與 device_id '{device_id}' 關聯的使用者")
                    time.sleep(3)
                    continue

                # 建立圖片 URL
                original_content_url = f"{BASE_URL}/{photo_storage}"
                preview_image_url = f"{BASE_URL}/{photo_storage}"
                print(preview_image_url)
                logging.info(f"Photo URL: {preview_image_url}")

                # 遍歷所有綁定的 user_line 並發送照片
                for user_tuple in user_result:
                    user_id = user_tuple[0]  # 提取 user_line
                    logging.info(f"Sending photo to user: {user_id}")
                    try:
                        # 傳送照片訊息
                        image_message = ImageSendMessage(
                            original_content_url=original_content_url,
                            preview_image_url=preview_image_url
                        )
                        text_message = TextSendMessage(
                            text=f"這是{devicename}即時照片，已成功傳送！"
                        )
                        line_bot_api.push_message(user_id, [image_message, text_message])
                        logging.info(f"Successfully sent photo to {user_id}")
                    except LineBotApiError as send_error:
                        logging.error(f"Failed to send photo to {user_id}: {send_error}")

                # 所有訊息發送完成後，更新資料庫
                try:
                    db.update("UPDATE device SET photo_take = '0' WHERE device_id = %s;", (device_id,))
                    db.update("UPDATE photo SET msg = '1' WHERE photo_id = %s;", (photo_id,))
                    logging.info(f"Updated database for device_id: {device_id}, photo_id: {photo_id}")
                except Exception as db_error:
                    logging.error(f"Failed to update database: {db_error}")

            # 等待下一輪
            time.sleep(3)

        except pymysql.MySQLError as db_error:
            logging.error(f"Database error: {db_error}")
            db.reconnect()  # 嘗試重新連線
            time.sleep(10)  # 等待一段時間後重試
        except Exception as e:
            logging.error(f"Unexpected error in polling: {e}")
            time.sleep(10)  # 等待一段時間後重試

@app.route('/history/<filename>')
def send_history_photo(filename):
    # 返回指定的歷史圖片文件
    return send_from_directory('history', filename)


@handler.add(MessageEvent)
def echo(event):
    user_line = event.source.user_id
    user_input = event.message.text.strip()

    # 狀態變量
    global user_states
    if 'user_states' not in globals():
        user_states = {}

    if user_line not in user_states:
        user_states[user_line] = {'waiting_for_device_id': False, 'waiting_for_device_choice': False, 'pending_action': None, 'waiting_for_interval': False}

    # 獲取 device_name 的輔助函數
    def get_device_name(device_id):
        dname_sql = "SELECT `device_name` FROM `device` WHERE `device_id` = %s;"
        devi_name = db.select(dname_sql, (device_id,))
        return devi_name[0][0] if devi_name else "未知裝置"

    # 狀態: 等待選擇裝置 (使用 device_name 顯示)
    if user_states[user_line].get('waiting_for_device_choice'):
        selected_device_name = user_input.strip()
        # 根據 device_name 查找對應的 device_id
        sql_find_device = "SELECT device_id FROM device WHERE device_name = %s;"
        device_data = db.select(sql_find_device, (selected_device_name,))
        
        if device_data:
            device_id = device_data[0][0]
            sql_check_binding = "SELECT device_id FROM user WHERE user_line = %s AND device_id = %s;"
            binding_data = db.select(sql_check_binding, (user_line, device_id))

            if binding_data:
                user_states[user_line]['selected_device_id'] = device_id
                user_states[user_line]['waiting_for_device_choice'] = False
                pending_action = user_states[user_line]['pending_action']

                if pending_action == '裝置拍照':
                    sql_update_take_photo = "UPDATE `device` SET `take_photo` = '1' WHERE device_id = %s;"
                    try:
                        db.update(sql_update_take_photo, (device_id,))
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(f'已選擇裝置{selected_device_name}，拍照功能已啟用。')
                        )
                    except Exception as e:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(f'已選擇裝置{selected_device_name}，但設定拍照功能時發生錯誤: {e}')
                        )

                elif pending_action == '查詢裝置歷史紀錄':
                    generate_last_7days_chart(device_id, db)
                    now = datetime.now()
                    today_date = now.strftime("%Y-%m-%d")
                    image_url = f"{BASE_URL}/history/{selected_device_name}_{today_date}_7days_mosquito_history.png"
                    line_bot_api.reply_message(
                        event.reply_token,
                        ImageSendMessage(
                            original_content_url=image_url,
                            preview_image_url=image_url
                        )
                    )

                elif pending_action == '調整拍照間隔時間':
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(f'已選擇裝置 {selected_device_name}，請輸入想要設定的拍照間隔時間（秒）。')
                    )
                    user_states[user_line]['waiting_for_interval'] = True

                elif pending_action == '重置裝置':
                    temp_sql = "UPDATE device SET temp = -1 WHERE device_id = %s;"
                    db.update(temp_sql, (device_id,))
                    reply_text = f'已選擇裝置{selected_device_name}，已重置。'
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=reply_text)
                    )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('你輸入的裝置名稱未綁定，請從你的綁定清單中選擇一個有效的裝置名稱。')
                )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('輸入的裝置名稱不存在，請輸入正確的裝置名稱。')
            )
        return

    # 狀態: 等待拍照間隔時間輸入
    if user_states[user_line].get('waiting_for_interval'):
        device_id = user_states[user_line]['selected_device_id']
        device_name = get_device_name(device_id)
        try:
            number = int(user_input.strip())
            reply_text = f'裝置{device_name}的拍照時間已設為：{number}秒'
            sql_check_time = "SELECT take_time FROM device WHERE device_id = %s;"
            existing_time = db.select(sql_check_time, (device_id,))

            if existing_time:
                sql_update_time = "UPDATE device SET take_time = %s WHERE device_id = %s;"
                db.update(sql_update_time, (number, device_id))
            else:
                sql_insert_time = "INSERT INTO device (device_id, take_time) VALUES (%s, %s);"
                db.insert(sql_insert_time, (device_id, number))

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('請輸入有效的數字作為拍照間隔時間（例如 "10" 表示 10 秒）。')
            )
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(f'設定拍照間隔時間時發生錯誤: {e}')
            )
        user_states[user_line]['waiting_for_interval'] = False
        return

    # 狀態: 等待裝置 ID 輸入（綁定流程，保持使用 device_id）
    if user_states[user_line]['waiting_for_device_id']:
        device_id = user_input.strip()
        if re.fullmatch(r"[A-Za-z0-9]{2,100}", device_id):
            sql_check_device = "SELECT device_name FROM device WHERE device_id = %s;"
            device_data = db.select(sql_check_device, (device_id,))

            if device_data:
                device_name = device_data[0][0]
                sql_check_binding = "SELECT * FROM user WHERE user_line = %s AND device_id = %s;"
                binding_data = db.select(sql_check_binding, (user_line, device_id))

                if not binding_data:
                    sql_insert_device = "INSERT INTO user (user_line, device_id) VALUES (%s, %s);"
                    db.insert(sql_insert_device, (user_line, device_id))
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(f'裝置 {device_name}（ID: {device_id}）已成功綁定！\n如果還想新增其他裝置，請再次輸入 "新增裝置綁定"。')
                    )
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(f'裝置 {device_name}（ID: {device_id}）已綁定過，請輸入其他未綁定的裝置 ID。')
                    )
                user_states[user_line]['waiting_for_device_id'] = False
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('該裝置 ID 不存在，請重新輸入正確的裝置 ID。')
                )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('裝置 ID 只能包含英文字母和數字，且長度在 2 到 100 之間，請重新輸入。')
            )
        return

    # 檢查已綁定的裝置 (顯示 device_name)
    sql_check = "SELECT device_id FROM user WHERE user_line = %s;"
    user_info = db.select(sql_check, (user_line,))
    bound_device_names = [get_device_name(row[0]) for row in user_info] if user_info else []

    # 處理「新增裝置綁定」
    if user_input.lower() == "新增裝置綁定":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('請問要綁定的裝置 ID 是什麼？')
        )
        user_states[user_line]['waiting_for_device_id'] = True
        return

    # 未綁定裝置的情況
    if not user_info:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('你尚未綁定任何裝置。\n請先輸入 "新增裝置綁定" 來綁定一台裝置。')
        )
        return

    # 有綁定裝置的情況
    # 處理「查詢裝置網頁」（不需選擇裝置）
    if user_input == '查詢裝置網頁':
        reply_text = "歡迎使用網頁查詢服務！以下是我們的查詢網站："
        reply_url = "http://120.126.17.57:5001"
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text=reply_text),
                TextSendMessage(text=reply_url)
            ]
        )
        return

    # 需要選擇裝置的功能清單
    device_required_actions = ['裝置拍照', '查詢裝置歷史紀錄', '調整拍照間隔時間', '重置裝置']

    # 綁定多台裝置的情況 (顯示 device_name)
    if len(user_info) > 1:
        if user_input in device_required_actions:
            bound_devices = ", ".join(bound_device_names)
            user_states[user_line]['waiting_for_device_choice'] = True
            user_states[user_line]['pending_action'] = user_input
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(f'你已綁定多台裝置：{bound_devices}。\n請輸入你要操作的裝置名稱。')
            )
            return
    else:
        device_id = user_info[0][0]  # 綁定一台裝置時直接使用
        device_name = get_device_name(device_id)

        # 執行功能（已綁定一台裝置）
        if user_input == '裝置拍照':
            sql_update_take_photo = "UPDATE `device` SET `take_photo` = '1' WHERE device_id = %s;"
            try:
                db.update(sql_update_take_photo, (device_id,))
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(f'裝置 {device_name} 拍照功能已啟用。')
                )
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(f'裝置{device_name} 設定拍照功能時發生錯誤: {e}')
                )

        elif user_input == '查詢裝置歷史紀錄':
            generate_last_7days_chart(device_id, db)
            now = datetime.now()
            today_date = now.strftime("%Y-%m-%d")
            image_url = f"{BASE_URL}/history/{device_name}_{today_date}_7days_mosquito_history.png"
            line_bot_api.reply_message(
                event.reply_token,
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            )

        elif user_input == '調整拍照間隔時間':
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(f'請輸入裝置 {device_name} 的拍照間隔時間（秒）。')
            )
            user_states[user_line]['waiting_for_interval'] = True
            user_states[user_line]['selected_device_id'] = device_id

        elif user_input == '重置裝置':
            temp_sql = "UPDATE device SET temp = -1 WHERE device_id = %s;"
            db.update(temp_sql, (device_id,))
            reply_text = f'裝置 {device_name} 已重置。'
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )

    # 未匹配任何功能時的回應 (顯示 device_name)
    if not user_states[user_line].get('waiting_for_device_choice') and user_input.lower() != "新增裝置綁定":
        bound_devices = ", ".join(bound_device_names)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(f'你的 LINE ID 已綁定以下裝置：{bound_devices}。\n請輸入功能指令，例如 "裝置拍照" 或 "新增裝置綁定"。')
        )
 
if __name__ == "__main__":
    #原本主程式
    folder_path = "./uploads"

    # 啟動 Flask 作為一個單獨的線程
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000))
    flask_thread.daemon = True
    flask_thread.start()

    # 主線程中啟動照片輪詢線程
    monitor_thread = threading.Thread(target=monitor_and_send_photos, args=())
    monitor_thread.daemon = True
    monitor_thread.start()
    
    threading.Thread(target=process_queue(photo_queue,db), daemon=True).start()

    # 保持主程序運行，防止退出
    while True:
        time.sleep(1)
