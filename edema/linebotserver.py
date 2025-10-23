from flask import Flask, request, abort, send_from_directory , jsonify
from flask_cors import CORS
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from flask.logging import create_logger
from linebot.models import (
    MessageEvent, TextSendMessage, RichMenu, RichMenuArea, RichMenuSize,
    RichMenuBounds, MessageAction, ImageSendMessage, FlexSendMessage,
    BubbleContainer, BoxComponent, TextComponent, ButtonComponent
)
from tools.SQL import Database
from datetime import datetime as dt, timedelta
import threading
import time
import math
import json
import os
import logging
#for image create
import matplotlib.pyplot as plt
import pygame as pg
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import interp1d 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask and Line Bot setup
app = Flask(__name__)
CORS(app)  # 🔁 允許前端跨域請求

VITE_DIST_DIR = os.path.join(os.path.dirname(__file__), 'vite-project', 'dist')

db = Database(host='127.0.0.1', port=3306, user='root', passwd='', database='edema')
LOG = create_logger(app)
line_bot_api = LineBotApi('q3JVzzZMFT3uNo3WExjbE2i90qtTmP1TgdWpPOwPLSg/doEcypG+AR2gKqs+tQm1j1MD/UwNdj/FnaHySWILidNTupCnM10ibKrT4moG2nkjmKHXFwpwJGYWdPlnmwx0PXPXz+NA42UsVC+J/2GfaAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('306e6fd7572e026ee719e1e4eb2ebca6')
ngrok = 'https://edema.ngrok.app/'
PHOTO_DIR = os.path.join(app.root_path, 'history')

# Initialize database
db = Database(host='127.0.0.1', port=3306, user='root', passwd='', database='edema')

CORS(app)  # 🔁 允許前端跨域請求
# 需要操作的關鍵詞列表
TRIGGER_KEYWORDS = ['查詢資料', '開始', '校正', '測量歷史', '編輯資料', '表單填寫']
a_L = []
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    logger.info(f"Signature: {signature}")
    body = request.get_data(as_text=True)
    LOG.info(f"Request body: {body}")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)
    return 'OK'


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    sql = "SELECT * FROM account WHERE username = %s AND password = %s LIMIT 1"
    result = db.select(sql, (username, password))

    if result:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False}), 401


@app.route('/api/patients')
def get_patients():
    sql = """
        SELECT 
            p.patient_id,
            p.name,
            p.gender,
            p.height,
            p.weight,
            (
                SELECT MAX(f.measurement_time)
                FROM foot_data f
                WHERE f.patient_id = p.patient_id
            ) AS lastCheckDate
        FROM patients p;
    """
    results = db.select(sql)
    
    # 將資料轉為 dict 格式（因為 db.select 預設返回 tuple）
    keys = ['id', 'name', 'gender', 'height', 'weight', 'lastCheckDate']
    data = [dict(zip(keys, row)) for row in results]
    return jsonify(data)

@app.route('/api/patients/<int:patient_id>')
def get_patient(patient_id):
    sql = """
        SELECT 
            p.patient_id,
            p.name,
            p.gender,
            p.height,
            p.weight,
            (
                SELECT MAX(f.measurement_time)
                FROM foot_data f
                WHERE f.patient_id = p.patient_id
            ) AS lastCheckDate
        FROM patients p
        WHERE p.patient_id = %s;
    """
    result = db.select(sql, (patient_id,))
    if not result:
        return jsonify({'error': 'Patient not found'}), 404

    keys = ['id', 'name', 'gender', 'height', 'weight', 'lastCheckDate']
    data = dict(zip(keys, result[0]))
    
    return jsonify(data)

@app.route('/api/patients/<int:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    data = request.json
    sql = """
        UPDATE patients
        SET name = %s,
            gender = %s,
            height = %s,
            weight = %s
        WHERE patient_id = %s
    """
    db.update(sql, (data['name'], data['gender'], data['height'], data['weight'], patient_id))
    return jsonify({'message': 'Patient updated successfully'})

@app.route('/api/patients/<int:patient_id>/foot_data')
def get_foot_data(patient_id):
    sql = f"""
        SELECT
            f.id,
            f.mark_t AS mark,
            f.measurement_time AS time,
            f.d_measurement AS manual,
            f.circumference,
            f.area,
            f.photo_path,
            f.remark,
            COALESCE((
                SELECT qr.score
                FROM questionnaire_results qr
                WHERE qr.patient_id = f.patient_id
                  AND DATE(qr.submission_time) = DATE(f.measurement_time)
                LIMIT 1
            ), '-') AS survey
        FROM foot_data f
        WHERE f.patient_id = {patient_id}
        ORDER BY f.measurement_time DESC
    """
    results = db.select(sql)
    keys = ['id','mark','time', 'manual', 'circumference', 'area','photo_path','remark', 'survey']
    data = [dict(zip(keys, row)) for row in results]
    return jsonify(data)

@app.route('/api/patients/<int:patient_id>/foot_data/<int:_id>', methods=['DELETE'])
def delete_foot_data(patient_id, _id):
    try:
        sql = """
            DELETE FROM foot_data 
            WHERE patient_id = %s AND id = %s
        """
        print(sql, (patient_id, _id))
        db.update(sql, (patient_id, _id))
        return jsonify({'message': 'Deleted successfully'}), 200
    except Exception as e:
        print(f"Delete error: {e}")
        return jsonify({'error': 'Failed to delete'}), 500
    

@app.route('/photo/<path:filename>')
def serve_photo(filename):
    file_path = os.path.join(PHOTO_DIR, filename)
    if not os.path.isfile(file_path):
        abort(404)
    return send_from_directory(PHOTO_DIR, filename)

@app.route('/api/foot_data/<int:entry_id>', methods=['PUT'])
def update_foot_data(entry_id):
    data = request.get_json()
    manual = data.get('manual')
    remark = data.get('remark')
    mark = data.get('mark')
    sql = """
        UPDATE foot_data
        SET d_measurement = %s,
            remark = %s,
            mark_t = %s
        WHERE id = %s
    """
    try:
        db.update(sql, (manual, remark, mark, entry_id))
        return jsonify({'message': 'Foot data updated successfully'}), 200
    except Exception as e:
        print(f"Error updating foot data: {e}")
        return jsonify({'error': 'Failed to update foot data'}), 500

@app.route('/api/update_account', methods=['POST'])
def update_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    print(username, password)
    sql = "UPDATE account SET username=%s, password=%s WHERE id = 1 "
    db.update(sql, (username, password))
    return jsonify({'success': True})

def delete_existing_rich_menus():
    try:
        rich_menus = line_bot_api.get_rich_menu_list()
        for menu in rich_menus:
            line_bot_api.delete_rich_menu(menu.rich_menu_id)
            logger.info(f"Deleted Rich Menu: {menu.rich_menu_id}")
    except Exception as e:
        logger.error(f"Error deleting Rich Menu: {e}")

def create_rich_menu():
    button1 = RichMenuArea(
        bounds=RichMenuBounds(x=1250, y=843, width=1250, height=843),
        action=MessageAction(label='表單填寫', text='表單填寫')
    )
    button2 = RichMenuArea(
        bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
        action=MessageAction(label='編輯資料', text='編輯資料')
    )
    button3 = RichMenuArea(
        bounds=RichMenuBounds(x=0, y=843, width=1250, height=843),
        action=MessageAction(label='測量歷史', text='測量歷史')
    )
    button4 = RichMenuArea(
        bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
        action=MessageAction(label='查詢資料', text='查詢資料')
    )

    rich_menu = RichMenu(
        size=RichMenuSize(width=2500, height=1686),
        selected=True,
        name='function',
        chat_bar_text='功能選單',
        areas=[button1, button2, button3, button4]
    )

    try:
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu)
        logger.info(f'Rich Menu created. rich_menu_id: {rich_menu_id}')
        if os.path.exists('p.png'):
            with open('p.png', 'rb') as f:
                line_bot_api.set_rich_menu_image(rich_menu_id, 'image/png', f)
                logger.info('Rich Menu image uploaded.')
        else:
            logger.error("Rich menu image file not found")
        line_bot_api.set_default_rich_menu(rich_menu_id)
        logger.info('Rich Menu set as default.')
    except Exception as e:
        logger.error(f'Error creating Rich Menu: {e}')

@app.route('/history/<patient_id>/<path:filename>')
def send_history_photo(patient_id, filename):
    history_path = f'history/{patient_id}'
    if os.path.exists(os.path.join(history_path, filename)):
        return send_from_directory(history_path, filename)
    else:
        logger.error(f"History file not found: {os.path.join(history_path, filename)}")
        abort(404)

@app.route('/photo/<path:filename>')
def send_photo(filename):
    if os.path.exists(os.path.join('photo', filename)):
        return send_from_directory('photo', filename)
    else:
        logger.error(f"Photo file not found: {os.path.join('photo', filename)}")
        abort(404)

@app.route('/data', methods=['POST'])
def receive_data():
    global a_L,global_server_state
    req = request.get_json()
    point_len = 90

    if req and 'userId' in req and 'data' in req:
        user_id = req['userId']
        data_values = req['data']
        if isinstance(data_values, list):
            a_L.extend(data_values)
            print("Received data from user:", user_id)
            print("Data count:", len(a_L))
            if len(a_L) >= point_len:
                global_server_state = 0
                print("Full data:", a_L)
            
                # 分割數據
                point = json.dumps(a_L[:point_len // 2], separators=(',', ':'))
                point2 = json.dumps(a_L[point_len // 2:], separators=(',', ':'))
            
                # 處理數據並計算面積與周長（**先做這步**）
                image_path, leg_area, leg_size = generate_leg_image(a_L, str(user_id))
                print(round((leg_size/10),2))  # 周長（取整）
                print(round((leg_area/100),2))
                # 設定基本資訊
                measurement_time = dt.now().strftime('%Y-%m-%d %H:%M:%S')
                notified = 1
                patient_id = user_id
            
                # 組合插入語句（**一次性寫入**）
                sql = """
                    INSERT INTO foot_data (
                        patient_id, measurement_time, notified, point, point2,
                        circumference, area, photo_path
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    patient_id,
                    measurement_time,
                    notified,
                    point,
                    point2,
                    round((leg_size/10),2),  # 周長（取整）
                    round((leg_area/100),2),  # 面積（取整）
                    image_path             # 圖片路徑
                )
                db.insert(sql, params)
                print("Data inserted into database with image, area, and perimeter")
            
                # 清空暫存
                a_L.clear()
                db.update(f"DELETE FROM device_table WHERE test_id = {int(user_id)};")
            
                return jsonify({
                    "status": "Data processed",
                    "count": 270,
                    "area": leg_area,
                    "perimeter": leg_size
                }), 200
            else:
                return jsonify({"status": "Data received", "count": len(a_L)}), 200
        else:
            return "Data is not in expected format", 400
    else:
        return "Invalid request", 400
    
@app.route('/get_test', methods=['GET'])
def serach_id():
    try:
        ID = db.select('SELECT * FROM `device_table`;')[0][0]
    except:
        ID = -1
    return jsonify({"userid":ID})

def remove_outliers(data, threshold=2):
    mean = np.mean(data)
    std_dev = np.std(data)
    return [x if abs(x - mean) <= threshold * std_dev else mean for x in data]

def generate_leg_image(IR_list, patient_id):
    # 移除異常值
    filtered_data = remove_outliers(IR_list, threshold=2)
    sort_filtered_data = remove_outliers(sorted(IR_list), threshold=2)
    # 使用高斯濾波平滑數據
    smoothed_data = gaussian_filter1d(filtered_data, sigma=3)
    sort_smoothed_data = gaussian_filter1d(sort_filtered_data, sigma=3)
    # 插值增強數據點數量
    num_points = 270  # 目標插值後的數據點數量
    x_original = np.linspace(0, 1, len(smoothed_data))
    x_interp = np.linspace(0, 1, num_points)
    interpolator = interp1d(x_original, smoothed_data, kind="cubic")
    interpolated_data = interpolator(x_interp)
    
    sx_original = np.linspace(0, 1, len(sort_smoothed_data))
    sx_interp = np.linspace(0, 1, num_points)
    sinterpolator = interp1d(sx_original, sort_smoothed_data, kind="cubic")
    sinterpolated_data = sinterpolator(sx_interp)
    
    
    """根據 IR_list 生成腳部影像並儲存為 PNG"""
    pg.init()
    pg.display.set_mode((900, 600), pg.HIDDEN)
    screen = pg.Surface((900, 600))
    btn_font = pg.font.Font("./font/BAHNSCHRIFT.ttf", 16)

    r = 225  # 半徑，確保為浮點數
    transform_rate = 10.0  # 轉換比例，確保為浮點數
    valid_points = [(i, float(value)) for i, value in enumerate(interpolated_data) if value not in [0, None]]
    sort_valid_points = [(i, float(value)) for i, value in enumerate(sinterpolated_data) if value not in [0, None]]
     
    # 重新計算有效點的數量和角度
    num_valid_points = len(valid_points)
    if num_valid_points < 3:
        print("有效點數不足，無法生成圖像。")
        return None
    angle = 360.0 / num_valid_points  # 每個點的角度間隔，使用浮點數
    points = [] ; sort_points = []
    leg_len = [] ; s_leg_len = []

    current_time = dt.now().strftime("%Y%m%d%H%M")

    # 計算每個點的座標
    for i, value in valid_points:
        actual_len = r - value * transform_rate
        leg_y = actual_len * math.sin(math.radians(i * angle))
        leg_x = actual_len * math.cos(math.radians(i * angle))
        point = (450.0 - leg_y * 0.7, 300.0 - leg_x * 0.7)
        leg_len.append(actual_len)
        points.append(point)
    
    for i, value in sort_valid_points:
        actual_len = r - value * transform_rate
        s_leg_y = actual_len * math.sin(math.radians(i * angle))
        s_leg_x = actual_len * math.cos(math.radians(i * angle))
        s_point = (450.0 - s_leg_y * 0.7, 300.0 - s_leg_x * 0.7)
        s_leg_len.append(actual_len)
        sort_points.append(s_point)
    def calculate_area_and_perimeter(sort_points,points):
        n = len(points)
        area = 0
        perimeter = 0
        max_length = 0
        min_length = float('inf')
        max_points = (points[0], points[1])
        min_points = (points[0], points[1])
        
        for i in range(n-1):
            x , y = points[i]
            x1, y1 = sort_points[i]
            x2, y2 = sort_points[(i + 1) % n]
            len_1 = s_leg_len[i]
            len_2 = s_leg_len[(i + 1) % n]
            area += (0.5 * math.sin(math.radians(angle)) * len_1 * len_2)
            perimeter += math.hypot(x2 - x1, y2 - y1)#math.sqrt(len_1 ** 2 + len_2 ** 2 - 2 * len_1 * len_2 * math.cos(math.radians(angle)))
           # print(i,((i + 1) % n),perimeter,area)
            
            if leg_len[i] > max_length:
                max_length = leg_len[i]
                max_points = (x,y)

            if leg_len[i] < min_length:
                min_length = leg_len[i]
                min_points = (x,y) 
        return area, perimeter, max_points, max_length / transform_rate, min_points, min_length / transform_rate
    leg_area, leg_size, max_line_points, max_len, min_line_points, min_len = calculate_area_and_perimeter(sort_points,points)
    real_time = time.ctime(time.time())

    # 繪製畫面
    screen.fill((255, 255, 255))
    pg.draw.line(screen, (200, 200, 200), (150, 300), (750, 300), 3)
    pg.draw.line(screen, (200, 200, 200), (450, 50), (450, 550), 3)

    screen.blit(btn_font.render(f"User ID : {patient_id}", True, (70, 70, 70)), (50, 50))
    screen.blit(btn_font.render(f"Measurement time : {real_time}", True, (70, 70, 70)), (50, 80))
    screen.blit(btn_font.render(f"Measured rotation angle: {angle:.1f} degree", True, (70, 70, 70)), (50, 110))
    screen.blit(btn_font.render(f"Ankle area : {round(leg_area / (transform_rate ** 2), 2)} cm^2", True, (70, 70, 70)), (50, 140))
    screen.blit(btn_font.render(f"Ankle circumference : {round(leg_size / transform_rate, 2)} cm", True, (70, 70, 70)), (50, 170))
    pg.draw.rect(screen, (30,78,119), [50, 210, 20, 10], 0)
    screen.blit(btn_font.render("Maximum length", True, (70,70,70)), (80, 205))
    pg.draw.rect(screen, (255,0,0), [50, 240, 20, 10], 0)
    screen.blit(btn_font.render("Minimum length", True, (70,70,70)), (80, 235))

    if len(points) > 2:
        pg.draw.polygon(screen, (255, 200, 200), points, 0)
        pg.draw.polygon(screen, (150, 150, 150), points, 1)

    pg.draw.line(screen, (70, 70, 70), (450, 300), max_line_points, 2)
    screen.blit(btn_font.render(f"Max:{round(max_len,1)}", True, (70, 70, 70)),
                ((450 + max_line_points[0]) // 2 - 30, (300 + max_line_points[1]) // 2 - 30))
    pg.draw.line(screen, (255,0,0), (450, 300), min_line_points, 2)
    screen.blit(btn_font.render(f"Min:{round(min_len,1)}", True, (80,80,80)), 
                ((450 + min_line_points[0]) // 2 - 40, (300 + min_line_points[1]) // 2 - 40))

    # 儲存 PNG 圖片，根據病患 ID 命名
    # image_path = f"./photo/{current_time}_patient_{patient_id}.png"
    # pg.image.save(screen, image_path)
    # print(f"Screenshot saved as {image_path}!")

    # pg.quit()
    # return image_path , leg_area, leg_size

    os.makedirs('photo', exist_ok=True)
    os.makedirs(f'history/{patient_id}', exist_ok=True)
    image_path = f"photo/{current_time}_patient_{patient_id}.png"
    history_path = f"history/{patient_id}/{current_time}_patient_{patient_id}.png"
    pg.image.save(screen, image_path)
    pg.image.save(screen, history_path)
    logger.info(f"Screenshot saved as {image_path} and {history_path}")
    pg.quit()
    return history_path , leg_area, leg_size

    # # 移除異常值
    # filtered_data = remove_outliers(IR_list, threshold=2)

    # # 使用高斯濾波平滑數據
    # smoothed_data = gaussian_filter1d(filtered_data, sigma=3)

    # # 插值增強數據點數量
    # num_points = 270  # 目標插值後的數據點數量
    # x_original = np.linspace(0, 1, len(smoothed_data))
    # x_interp = np.linspace(0, 1, num_points)
    # interpolator = interp1d(x_original, smoothed_data, kind="cubic")
    # interpolated_data = interpolator(x_interp)
    # """根據 IR_list 生成腳部影像並儲存為 PNG"""
    # pg.init()
    # pg.display.set_mode((900, 600), pg.HIDDEN)
    # screen = pg.Surface((900, 600))
    # btn_font = pg.font.Font("./font/BAHNSCHRIFT.ttf", 16)

    # r = 228  # 半徑，確保為浮點數
    # transform_rate = 10.0  # 轉換比例，確保為浮點數
    # valid_points = [(i, float(value)) for i, value in enumerate(interpolated_data) if value not in [0, None]]

    # # 重新計算有效點的數量和角度
    # num_valid_points = len(valid_points)
    # if num_valid_points < 3:
    #     print("有效點數不足，無法生成圖像。")
    #     return None
    # angle = 360.0 / num_valid_points  # 每個點的角度間隔，使用浮點數
    # points = []
    # leg_len = []

    # current_time = dt.now().strftime("%Y%m%d%H%M")

    # # 計算每個點的座標
    # for i, value in valid_points:
    #     actual_len = r - value * transform_rate
    #     leg_y = actual_len * math.sin(math.radians(i * angle))
    #     leg_x = actual_len * math.cos(math.radians(i * angle))
    #     point = (450.0 - leg_y * 0.7, 300.0 - leg_x * 0.7)
    #     leg_len.append(actual_len)
    #     points.append(point)
        
    # def calculate_area_and_perimeter(points):
    #     n = len(points)
    #     area = 0
    #     perimeter = 0
    #     max_length = 0
    #     min_length = float('inf')
    #     max_points = (points[0], points[1])
    #     min_points = (points[0], points[1])

    #     for i in range(n):
    #         x1, y1 = points[i]
    #         x2, y2 = points[(i + 1) % n]
    #         len_1 = leg_len[i]
    #         len_2 = leg_len[(i + 1) % n]
    #         area += (0.5 * math.sin(math.radians(angle)) * len_1 * len_2)
    #         perimeter += math.hypot(x2 - x1, y2 - y1)#math.sqrt(len_1 ** 2 + len_2 ** 2 - 2 * len_1 * len_2 * math.cos(math.radians(angle)))
        
    #     # print(i,((i + 1) % n),perimeter,area)
            
    #         if leg_len[i] > max_length:
    #             max_length = leg_len[i]
    #             max_points = (x1, y1)

    #         if leg_len[i] < min_length:
    #             min_length = leg_len[i]
    #             min_points = (x1, y1)
            
    #     return area, perimeter, max_points, max_length / transform_rate, min_points, min_length / transform_rate
    # leg_area, leg_size, max_line_points, max_len, min_line_points, min_len = calculate_area_and_perimeter(points)
    # real_time = time.ctime(time.time())
    
    # # 繪製畫面
    # screen.fill((255, 255, 255))
    # pg.draw.line(screen, (200, 200, 200), (150, 300), (750, 300), 3)
    # pg.draw.line(screen, (200, 200, 200), (450, 50), (450, 550), 3)

    # screen.blit(btn_font.render(f"User ID : {patient_id}", True, (70, 70, 70)), (50, 50))
    # screen.blit(btn_font.render(f"Measurement time : {real_time}", True, (70, 70, 70)), (50, 80))
    # screen.blit(btn_font.render(f"Measured rotation angle: {angle:.1f} degree", True, (70, 70, 70)), (50, 110))
    # screen.blit(btn_font.render(f"Ankle area : {round(leg_area / (transform_rate ** 2), 2)} cm^2", True, (70, 70, 70)), (50, 140))
    # screen.blit(btn_font.render(f"Ankle circumference : {round(leg_size / transform_rate, 2)} cm", True, (70, 70, 70)), (50, 170))
    # pg.draw.rect(screen, (30,78,119), [50, 210, 20, 10], 0)
    # screen.blit(btn_font.render("Maximum length", True, (70,70,70)), (80, 205))
    # pg.draw.rect(screen, (255,0,0), [50, 240, 20, 10], 0)
    # screen.blit(btn_font.render("Minimum length", True, (70,70,70)), (80, 235))

    # if len(points) > 2:
    #     pg.draw.polygon(screen, (255, 200, 200), points, 0)
    #     pg.draw.polygon(screen, (150, 150, 150), points, 1)
    
    # pg.draw.line(screen, (70, 70, 70), (450, 300), max_line_points, 2)
    # screen.blit(btn_font.render(f"Max:{round(max_len,1)}", True, (70, 70, 70)),
    #             ((450 + max_line_points[0]) // 2 - 30, (300 + max_line_points[1]) // 2 - 30))
    # pg.draw.line(screen, (255,0,0), (450, 300), min_line_points, 2)
    # screen.blit(btn_font.render(f"Min:{round(min_len,1)}", True, (80,80,80)), 
    #             ((450 + min_line_points[0]) // 2 - 40, (300 + min_line_points[1]) // 2 - 40))

    # os.makedirs('photo', exist_ok=True)
    # os.makedirs(f'history/{patient_id}', exist_ok=True)
    # image_path = f"photo/{current_time}_patient_{patient_id}.png"
    # history_path = f"history/{patient_id}/{current_time}_patient_{patient_id}.png"
    # pg.image.save(screen, image_path)
    # pg.image.save(screen, history_path)
    # logger.info(f"Screenshot saved as {image_path} and {history_path}")
    # pg.quit()
    # return history_path , leg_area, leg_size
    # except Exception as e:
    #     logger.error(f"Error generating leg image: {e}")
    #     pg.quit()
    #     return None

def poll_and_notify():
    while True:
        try:
            entries = db.select("""
                SELECT p.line_id, f.patient_id, f.measurement_time, f.point, f.point2
                FROM patients p
                JOIN foot_data f ON f.patient_id = p.patient_id
                WHERE f.notified = 1;
            """)
            print(entries)
            if not entries:
                logger.info("No data to notify.")
                time.sleep(5)
                continue

            for entry in entries:
                patient_line_id, patient_id, measurement_time, point, point2 = entry

                if not point:
                    logger.error(f"No points data for patient {patient_id} at {measurement_time}")
                    continue

                try:
                    point_list = json.loads(point) if point else []
                    point2_list = json.loads(point2) if point2 and point2 != '[]' else []
                    IR_list = point_list + point2_list
                    IR_list = [float(x) if x is not None else 0 for x in IR_list]
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON format for points data: {e}")
                    continue

                image_path, leg_area, leg_size = generate_leg_image(IR_list, patient_id)
                
                if image_path:
                    try:
                        line_bot_api.push_message(
                            patient_line_id,
                            ImageSendMessage(
                                original_content_url=f"{ngrok}/{image_path}",
                                preview_image_url=f"{ngrok}/{image_path}"
                            )
                        )
                        message = f"Patient ID: {patient_id}\n這是您的測量結果。"
                        line_bot_api.push_message(
                            patient_line_id,
                            TextSendMessage(text=message)
                        )
                        db.update("""
                            UPDATE foot_data
                            SET notified = 0
                            WHERE patient_id = %s AND measurement_time = %s
                        """, (patient_id, measurement_time))
                        logger.info(f"Patient ID {patient_id} notified successfully.")
                    except Exception as e:
                        logger.error(f"Notification failed for Patient ID {patient_id}: {e}")
        except Exception as e:
            logger.error(f"Error during polling: {e}")
        time.sleep(30)

@app.route('/notify_foot_entry', methods=['POST'])
def notify_foot_entry():
    data = request.form
    logger.info(f"Received data: {json.dumps(data, ensure_ascii=False)}")
    try:
        patient_id = data.get('patient_id')
        points = data.get('points')
        measurement_time = dt.now().strftime('%Y-%m-%d %H:%M:%S')

        if not patient_id or not points:
            logger.error("Missing patient_id or points")
            return 'Missing patient_id or points', 400

        try:
            points_list = json.loads(points)
        except json.JSONDecodeError:
            logger.error("Invalid JSON format for points")
            return 'Invalid JSON format for points', 400

        max_length = 767
        point_list = points_list
        point2_list = []

        point_str = json.dumps(point_list)
        while len(point_str.encode('utf-8')) > max_length and point_list:
            point2_list.insert(0, point_list.pop())
            point_str = json.dumps(point_list)

        point2_str = json.dumps(point2_list) if point2_list else '[]'

        db.insert("""
            INSERT INTO foot_data (patient_id, measurement_time, notified, point, point2)
            VALUES (%s, %s, 1, %s, %s)
        """, (patient_id, measurement_time, point_str, point2_str))

        logger.info(f"Foot entry recorded for patient {patient_id}")
        return 'Foot entry recorded successfully', 200
    except Exception as e:
        logger.error(f"Error processing foot entry: {e}")
        return 'Data processing error', 500

# Questionnaire logic
user_states = {}
form_data = {}
form_data_scores = {}

def calculate_area_and_perimeter2(points, transform_rate=10.0):
    n = len(points)
    area = 0.0
    perimeter = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
        perimeter += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    area = abs(area) / 2.0
    return area / (transform_rate ** 2), perimeter / transform_rate

def generate_line_chart(patient_id, history_data, transform_rate=10.0, r=250.0):
    if not history_data:
        logger.info(f"No history data for patient {patient_id}")
        return None

    current_time = dt.now()
    two_weeks_ago = current_time - timedelta(days=14)

    processed_data = []
    for entry in history_data:
        measurement_time, point, point2 = entry
        try:
            if not isinstance(measurement_time, dt):
                measurement_time = dt.strptime(str(measurement_time), '%Y-%m-%d %H:%M:%S')
            if measurement_time >= two_weeks_ago:
                processed_data.append((measurement_time, point, point2))
        except ValueError as e:
            logger.error(f"Error parsing measurement_time {measurement_time}: {e}")
            continue

    if not processed_data:
        logger.info(f"No data within the last 14 days for patient {patient_id}")
        return None

    times = []
    perimeters = []
    areas = []

    for entry in processed_data:
        measurement_time, point, point2 = entry
        times.append(measurement_time)

        try:
            point_list = json.loads(point) if point else []
            point2_list = json.loads(point2) if point2 and point2 != '[]' else []
            IR_list = point_list + point2_list
            IR_list = [float(x) if x is not None else 0 for x in IR_list]
            logger.info(f"IR_list for {measurement_time}: {IR_list}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format for points data at {measurement_time}: {e}")
            continue

        if len(IR_list) < 3:
            logger.info(f"Skipping entry at {measurement_time}: Not enough points ({len(IR_list)})")
            continue

        angle = 360.0 / len(IR_list)
        points = []
        for i, value in enumerate(IR_list):
            actual_len = r - value * transform_rate
            leg_y = actual_len * math.sin(math.radians(i * angle))
            leg_x = actual_len * math.cos(math.radians(i * angle))
            point = (450.0 - leg_y * 0.7, 300.0 - leg_x * 0.7)
            points.append(point)

        area, perimeter = calculate_area_and_perimeter2(points, transform_rate)
        perimeters.append(perimeter) 
        areas.append(area)
        logger.info(f"Calculated for {measurement_time}: Area={area}, Perimeter={perimeter}")

    if not times:
        logger.info(f"No valid data points to plot for patient {patient_id}")
        return None

    plt.figure(figsize=(10, 6))
    plt.plot(times, perimeters, label='Perimeter (cm)', marker='o')
    plt.plot(times, areas, label='Area (cm²)', marker='s')
    
    plt.title(f'Patient ID: {patient_id}\nFoot Perimeter and Area Over Time')
    plt.xlabel('Measurement Time')
    plt.ylabel('Value')
    plt.legend()
    
    plt.xticks(ticks=times, labels=[t.strftime('%m-%d %H:%M') for t in times])
    plt.grid(True)
    
    for i in range(len(times)):
        plt.annotate(f'Perimeter: {perimeters[i]:.1f} cm', 
                     xy=(times[i], perimeters[i]), 
                     xytext=(10, 10), 
                     textcoords='offset points',
                     ha='left', va='bottom')
        plt.annotate(f'Area: {areas[i]:.1f} cm²', 
                     xy=(times[i], areas[i]), 
                     xytext=(10, -10), 
                     textcoords='offset points',
                     ha='left', va='top')

    plt.tight_layout()
    
    os.makedirs(f'history/{patient_id}', exist_ok=True)
    image_path = f"history/{patient_id}/{current_time.strftime('%Y%m%d%H%M')}_patient_{patient_id}_linechart.png"
    plt.savefig(image_path)
    plt.close()
    
    logger.info(f"Line chart generated for patient {patient_id}: {image_path}")
    return image_path

def format_question_text(question, max_chars=15):
    return '\n'.join([question[i:i+max_chars] for i in range(0, len(question), max_chars)])

def create_flex_message(question, options):
    formatted_question = format_question_text(question)
    bubble = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(
                    text=formatted_question,
                    weight='bold',
                    size='md',
                    wrap=True,
                    margin='md'
                ),
                BoxComponent(
                    layout='vertical',
                    spacing='md',
                    contents=[
                        ButtonComponent(
                            style='primary',
                            margin='sm',
                            action=MessageAction(
                                label=option,
                                text=option
                            )
                        ) for option in options
                    ]
                ),
                ButtonComponent(
                    style='secondary',
                    margin='lg',
                    action=MessageAction(
                        label='取消',
                        text='取消'
                    )
                )
            ]
        )
    )
    return FlexSendMessage(alt_text='問卷問題', contents=bubble)

questions = [
    {
        "text": "請問您今天是泡澡還是沖澡？",
        "options": ["泡澡", "沖澡", "擦澡", "不想洗澡", "因行動不便無法洗澡"],
        "sub_question": {
            "text": "在您洗澡的過程中，你是否會覺得累或感到喘？",
            "options": ["非常累或喘", "很累或喘", "相當累或喘", "有點累或喘", "一點都不累或喘"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer in ["泡澡", "沖澡", "擦澡"]
    },
    {
        "text": "有沒有去便利商店散步？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "在走路的過程中，是否有覺得累或感到喘？",
            "options": ["非常累或喘", "很累或喘", "相當累或喘", "有點累或喘", "一點也不累或喘"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "有沒有急著去做一件事？",
        "options": ["有", "沒有", "因行動不便無法走路"],
        "sub_question": {
            "text": "在走路的過程中，是否有覺得累或感到喘？",
            "options": ["非常累或喘", "很累或喘", "相當累或喘", "有點累或喘", "一點也不累或喘"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "今天早上起床，你是否有覺得腳部水腫？",
        "options": ["有", "沒有"],
        "scores": [0, 5]
    },
    {
        "text": "昨天有沒有因為疲憊(累)而去影響您去做您想做的事情呢？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "昨天大概有幾次因為疲憊(累)而去影響您去做您想做的事情呢？",
            "options": ["整天都累", "好多次", "1~3次"],
            "scores": [1, 1, 3]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "昨天有沒有因為呼吸急促(喘)而去影響您去做您想做的事情呢？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "昨天大概有幾次因為呼吸急促(喘)而去影響您去做您想做的事情呢？",
            "options": ["整天都累", "好多次", "1~3次"],
            "scores": [1, 1, 3]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "請問您昨天睡得好不好呢？",
        "options": ["好", "不好"],
        "sub_question": {
            "text": "是否有因為呼吸急促而造成您睡不好？",
            "options": ["有", "沒有"]
        },
        "sub_question_condition": lambda answer: answer == "不好"
    },
    {
        "text": "是否有因為呼吸急促而造成您睡不好？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "是否需要坐著或墊高頭部才改善？",
            "options": ["需要", "不需要"],
            "scores": [1, 3]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "昨天有沒有因為心臟衰竭的症狀影響您享受生活呢？",
        "options": ["有", "沒有"],
        "scores": [0, 5]
    },
    {
        "text": "您昨天有因為心臟不舒服而影響您從事興趣，休閒活動，運動嗎？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "請問您覺得影響程度為何呢？",
            "options": ["嚴重受到影響", "相當受到影響", "中度受到影響", "稍微受到影響", "並沒有受到影響"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "您昨天有因為心臟不舒服而影響您從事工作，家務嗎？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "請問您覺得影響程度為何呢？",
            "options": ["嚴重受到影響", "相當受到影響", "中度受到影響", "稍微受到影響", "並沒有受到影響"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "您昨天有因為心臟不舒服而影響您從事外出，拜訪朋友嗎？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "請問您覺得影響程度為何呢？",
            "options": ["嚴重受到影響", "相當受到影響", "中度受到影響", "稍微受到影響", "並沒有受到影響"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "您昨天有因為心臟不舒服而影響您從事開車，騎車嗎？",
        "options": ["有", "沒有", "無法執行"],
        "sub_question": {
            "text": "請問您覺得影響程度為何呢？",
            "options": ["嚴重受到影響", "相當受到影響", "中度受到影響", "稍微受到影響", "並沒有受到影響"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "請問您對目前心臟衰竭治療的改善情況，能不能接受呢？",
        "options": ["一點也不能接受", "大部分不能接受", "尚可接受", "大部分能接受", "完全沒有影響生活"],
        "scores": [1, 2, 3, 4, 5]
    }
]

def handle_action(event, user_id, patient_id, action):
    """處理特定動作的函數"""
    if action == '查詢資料':
        result = db.select("""
            SELECT name, height, gender, weight, level
            FROM patients
            WHERE patient_id = %s
        """, (patient_id,))

        if result:
            patient_name, height, gender, weight, level = result[0]
            text = f'姓名: {patient_name}\n身高: {height}\n性別: {gender}\n體重: {weight}\n等級: {level}'
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=text)
            )
            logger.info(f"Queried data for patient ID {patient_id}")
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='未查詢到相關資料')
            )
            logger.error(f"No data found for patient ID {patient_id}")

    elif action == '開始':
        try:
            db.update("UPDATE patients SET start = 1 WHERE patient_id = %s", (patient_id,))
            db.insert("INSERT INTO device_table (test_id) VALUES (%s)", (patient_id,))
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'病患 ID {patient_id} 的開始狀態已設定為 1，並已記錄至設備表。')
            )
            logger.info(f"Set start to 1 and added test_id {patient_id} to device_table")
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='更新開始狀態或設備表失敗，請稍後重試。')
            )
            logger.error(f"Error setting start or inserting test_id for patient {patient_id}: {e}")

    elif action == '校正':
        try:
            db.update("UPDATE patients SET correction = -1 WHERE patient_id = %s", (patient_id,))
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'病患 ID {patient_id} 的校正狀態已設定為 -1。')
            )
            logger.info(f"Set correction to -1 for patient ID {patient_id}")
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='更新校正狀態失敗，請稍後重試。')
            )
            logger.error(f"Error setting correction for patient ID {patient_id}: {e}")

    elif action == '測量歷史':
        history_data = db.select("""
            SELECT measurement_time, point, point2
            FROM foot_data
            WHERE patient_id = %s
            ORDER BY measurement_time
        """, (patient_id,))

        if not history_data:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='未查詢到測量歷史')
            )
            logger.error(f"No history data found for patient ID {patient_id}")
            return

        image_path = generate_line_chart(patient_id, history_data)
        if image_path:
            image_url = f"{ngrok}/{image_path}"
            line_bot_api.reply_message(
                event.reply_token,
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            )
            logger.info(f"Sent line chart history image for patient ID {patient_id}")
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='無法生成歷史折線圖，數據不足')
            )
            logger.error(f"Failed to generate line chart for patient ID {patient_id}")

    elif action == '編輯資料':
        user_states[user_id] = {'state': 'editing', 'patient_id': patient_id}
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請輸入要編輯的資料(輸入「身高」或「體重」)')
        )
        logger.info(f"User {user_id} started editing data for patient ID {patient_id}")

    elif action == '表單填寫':
        user_states[user_id] = {'current_question': 0, 'in_sub_question': False, 'patient_id': patient_id}
        form_data[user_id] = []
        form_data_scores[user_id] = []
        first_question = questions[0]
        line_bot_api.reply_message(
            event.reply_token,
            create_flex_message(first_question["text"], first_question["options"])
        )
        logger.info(f"User {user_id} started questionnaire for patient ID {patient_id}")

def handle_action(event, user_id, patient_id, action):
    """處理特定動作的函數"""
    if action == '查詢資料':
        result = db.select("""
            SELECT name, height, gender, weight, level
            FROM patients
            WHERE patient_id = %s
        """, (patient_id,))

        if result:
            patient_name, height, gender, weight, level = result[0]
            text = f'姓名: {patient_name}\n身高: {height}\n性別: {gender}\n體重: {weight}\n等級: {level}'
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=text)
            )
            logger.info(f"Queried data for patient ID {patient_id}")
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='未查詢到相關資料')
            )
            logger.error(f"No data found for patient ID {patient_id}")

    elif action == '開始':
        try:
            db.update("UPDATE patients SET start = 1 WHERE patient_id = %s", (patient_id,))
            db.insert("INSERT INTO device_table (test_id) VALUES (%s)", (patient_id,))
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'病患 ID {patient_id} 的開始狀態已設定為 1，並已記錄至設備表。')
            )
            logger.info(f"Set start to 1 and added test_id {patient_id} to device_table")
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='更新開始狀態或設備表失敗，請稍後重試。')
            )
            logger.error(f"Error setting start or inserting test_id for patient {patient_id}: {e}")

    elif action == '校正':
        try:
            db.update("UPDATE patients SET correction = -1 WHERE patient_id = %s", (patient_id,))
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'病患 ID {patient_id} 的校正狀態已設定為 -1。')
            )
            logger.info(f"Set correction to -1 for patient ID {patient_id}")
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='更新校正狀態失敗，請稍後重試。')
            )
            logger.error(f"Error setting correction for patient ID {patient_id}: {e}")

    elif action == '測量歷史':
        history_data = db.select("""
            SELECT measurement_time, point, point2
            FROM foot_data
            WHERE patient_id = %s
            ORDER BY measurement_time
        """, (patient_id,))

        if not history_data:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='未查詢到測量歷史')
            )
            logger.error(f"No history data found for patient ID {patient_id}")
            return

        image_path = generate_line_chart(patient_id, history_data)
        if image_path:
            image_url = f"{ngrok}/{image_path}"
            line_bot_api.reply_message(
                event.reply_token,
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            )
            logger.info(f"Sent line chart history image for patient ID {patient_id}")
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='無法生成歷史折線圖，數據不足')
            )
            logger.error(f"Failed to generate line chart for patient ID {patient_id}")

    elif action == '編輯資料':
        user_states[user_id] = {'state': 'editing', 'patient_id': patient_id}
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請輸入要編輯的資料(輸入「身高」或「體重」)')
        )
        logger.info(f"User {user_id} started editing data for patient ID {patient_id}")

    elif action == '表單填寫':
        user_states[user_id] = {'current_question': 0, 'in_sub_question': False, 'patient_id': patient_id}
        form_data[user_id] = []
        form_data_scores[user_id] = []
        first_question = questions[0]
        line_bot_api.reply_message(
            event.reply_token,
            create_flex_message(first_question["text"], first_question["options"])
        )
        logger.info(f"User {user_id} started questionnaire for patient ID {patient_id}")

@handler.add(MessageEvent)
def echo(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()
    logger.info(f"Received message from user {user_id}: {user_input}, current state: {user_states.get(user_id)}")

    # 檢查是否正在選擇姓名
    if user_states.get(user_id) == 'selecting_name':
        if user_input.lower() == '取消':
            user_states[user_id] = None
            user_states[user_id + '_pending_action'] = None
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='已取消操作，請重新輸入指令。')
            )
            logger.info(f"User {user_id} cancelled action selection")
            return
        patient_name = user_input
        patient_data = db.select("SELECT patient_id, name FROM patients WHERE name = %s", 
                                (patient_name,))
        if patient_data:
            patient_id = patient_data[0][0]
            pending_action = user_states[user_id + '_pending_action']
            user_states[user_id] = 'confirm_name'
            user_states[user_id + '_pending_patient_id'] = patient_id
            user_states[user_id + '_pending_action'] = pending_action
            user_states[user_id + '_pending_name'] = patient_name
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'請再次確認輸入的是{patient_name}嗎？（請再次輸入是或不是）')
            )
        else:
            user_states[user_id] = 'confirm_add_name'
            user_states[user_id + '_pending_name'] = patient_name
            user_states[user_id + '_pending_action'] = user_states.get(user_id + '_pending_action')
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'未找到姓名為「{patient_name}」的病患，是否要新增此病患？請回覆「是」或「否」。')
            )
        return

    # 檢查是否在確認姓名輸入是否正確
    elif user_states.get(user_id) == 'confirm_name':
        if user_input.lower() == '是':
            patient_id = user_states[user_id + '_pending_patient_id']
            pending_action = user_states[user_id + '_pending_action']
            user_states[user_id] = None
            user_states[user_id + '_pending_patient_id'] = None
            user_states[user_id + '_pending_action'] = None
            user_states[user_id + '_pending_name'] = None
            handle_action(event, user_id, patient_id, pending_action)
        elif user_input.lower() == '不是':
            user_states[user_id] = 'selecting_name'
            user_states[user_id + '_pending_patient_id'] = None
            user_states[user_id + '_pending_name'] = None
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請重新輸入病患姓名')
            )
            logger.info(f"User {user_id} re-entering patient name")
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請輸入「是」或「不是」。')
            )
        return

    # 檢查是否在確認新增姓名
    elif user_states.get(user_id) == 'confirm_add_name':
        if user_input.lower() == '是':
            patient_name = user_states[user_id + '_pending_name']
            pending_action = user_states[user_id + '_pending_action']
            try:
                db.insert("""
                    INSERT INTO patients (name, height, gender, level, weight, start, correction)
                    VALUES (%s, NULL, NULL, NULL, NULL, 0, 0)
                """, (patient_name,))
                patient_data = db.select("SELECT patient_id FROM patients WHERE name = %s", 
                                        (patient_name,))
                if patient_data:
                    patient_id = patient_data[0][0]
                    user_states[user_id] = None
                    user_states[user_id + '_pending_name'] = None
                    user_states[user_id + '_pending_action'] = None
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f'已新增病患姓名「{patient_name}」，病患 ID 為 {patient_id}。')
                    )
                    # 執行對應操作
                    handle_action(event, user_id, patient_id, pending_action)
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text='新增病患失敗，請稍後重試。')
                    )
                    logger.error(f"Failed to retrieve new patient_id for name {patient_name}, user {user_id}")
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text='新增病患失敗，請稍後重試。')
                )
                logger.error(f"Error adding patient for user {user_id}: {e}")
        elif user_input.lower() == '否':
            user_states[user_id] = None
            user_states[user_id + '_pending_name'] = None
            user_states[user_id + '_pending_action'] = None
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='已取消操作，請重新輸入指令。')
            )
            logger.info(f"User {user_id} cancelled adding new patient")
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請回覆「是」或「否」。')
            )
        return

    # 檢查是否正在新增姓名
    elif user_states.get(user_id) == 'adding_name':
        patient_name = user_input
        try:
            db.insert("""
                INSERT INTO patients (name, height, gender, level, weight, start, correction)
                VALUES (%s, NULL, NULL, NULL, NULL, 0, 0)
            """, (patient_name,))
            patient_data = db.select("SELECT patient_id FROM patients WHERE name = %s", 
                                    (patient_name,))
            if patient_data:
                patient_id = patient_data[0][0]
                user_states[user_id] = {'current_question': 0, 'in_sub_question': False, 'patient_id': patient_id}
                form_data[user_id] = []
                form_data_scores[user_id] = []
                first_question = questions[0]
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f'已新增病患姓名「{patient_name}」，病患 ID 為 {patient_id}。')
                )
                line_bot_api.reply_message(
                    event.reply_token,
                    create_flex_message(first_question["text"], first_question["options"])
                )
                logger.info(f"User {user_id} added new patient: ID {patient_id}, Name {patient_name}, started questionnaire")
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text='新增病患失敗，請稍後重試。')
                )
                logger.error(f"Failed to retrieve new patient_id for name {patient_name}, user {user_id}")
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='新增病患失敗，請稍後重試。')
            )
            logger.error(f"Error adding patient for user {user_id}: {e}")
        return

    # 檢查是否正在編輯資料
    elif isinstance(user_states.get(user_id), dict) and user_states[user_id].get('state') == 'editing':
        patient_id = user_states[user_id]['patient_id']
        if '身高' in user_input:
            user_states[user_id] = {'state': 'editing_height', 'patient_id': patient_id}
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請輸入要更改的身高(例如: 170)')
            )
            logger.info(f"User {user_id} editing height for patient ID {patient_id}")
        elif '體重' in user_input:
            user_states[user_id] = {'state': 'editing_weight', 'patient_id': patient_id}
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請輸入要更改的體重(例如: 65)')
            )
            logger.info(f"User {user_id} editing weight for patient ID {patient_id}")
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請輸入要編輯的資料(輸入「身高」或「體重」)')
            )
        return

    elif isinstance(user_states.get(user_id), dict) and user_states[user_id].get('state') == 'editing_height':
        patient_id = user_states[user_id]['patient_id']
        try:
            new_height = float(user_input)
            db.update("UPDATE patients SET height = %s WHERE patient_id = %s", (new_height, patient_id))
            user_states[user_id] = None
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'身高已更新為 {new_height} 公分')
            )
            logger.info(f"Updated height to {new_height} for patient ID {patient_id}")
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請輸入正確的數字格式的身高')
            )
            logger.error(f"Invalid height format for user {user_id}: {user_input}")
        return

    elif isinstance(user_states.get(user_id), dict) and user_states[user_id].get('state') == 'editing_weight':
        patient_id = user_states[user_id]['patient_id']
        try:
            new_weight = float(user_input)
            db.update("UPDATE patients SET weight = %s WHERE patient_id = %s", (new_weight, patient_id))
            user_states[user_id] = None
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'體重已更新為 {new_weight} 公斤')
            )
            logger.info(f"Updated weight to {new_weight} for patient ID {patient_id}")
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請輸入正確的數字格式的體重')
            )
            logger.error(f"Invalid weight format for user {user_id}: {user_input}")
        return

    # 檢查是否正在填寫表單
    elif user_id in user_states and isinstance(user_states[user_id], dict) and 'current_question' in user_states[user_id]:
        state = user_states[user_id]
        patient_id = state.get('patient_id')
        current_question_idx = state["current_question"]
        
        if user_input.lower() == '取消':
            user_states.pop(user_id, None)
            form_data.pop(user_id, None)
            form_data_scores.pop(user_id, None)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='已取消表單填寫。')
            )
            logger.info(f"User {user_id} cancelled questionnaire for patient ID {patient_id}")
            return

        if current_question_idx >= len(questions):
            show_results(event, user_id, patient_id)
            return

        current_question = questions[current_question_idx]

        try:
            if state["in_sub_question"]:
                sub_question = current_question["sub_question"]
                if user_input in sub_question["options"]:
                    form_data[user_id].append((f"{current_question_idx + 1}(b): {sub_question['text']}", user_input))
                    if "scores" in sub_question:
                        index = sub_question["options"].index(user_input)
                        score = sub_question["scores"][index]
                        form_data_scores[user_id].append((f"q{current_question_idx + 1}_b", score))
                    else:
                        form_data_scores[user_id].append((f"q{current_question_idx + 1}_b", None))
                    state["in_sub_question"] = False
                    state["current_question"] += 1

                    if state["current_question"] < len(questions):
                        next_question = questions[state["current_question"]]
                        line_bot_api.reply_message(
                            event.reply_token,
                            create_flex_message(next_question["text"], next_question["options"])
                        )
                        logger.info(f"User {user_id} moved to question {state['current_question'] + 1} for patient ID {patient_id}")
                    else:
                        show_results(event, user_id, patient_id)
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"請選擇有效選項：{', '.join(sub_question['options'])}")
                    )
                    logger.error(f"Invalid sub-question option by user {user_id}: {user_input}")
            else:
                if user_input in current_question["options"]:
                    form_data[user_id].append((f"{current_question_idx + 1}(a): {current_question['text']}", user_input))
                    if "scores" in current_question:
                        index = current_question["options"].index(user_input)
                        score = current_question["scores"][index]
                        form_data_scores[user_id].append((f"q{current_question_idx + 1}_a", score))
                    else:
                        form_data_scores[user_id].append((f"q{current_question_idx + 1}_a", None))

                    if "sub_question" in current_question and current_question["sub_question_condition"](user_input):
                        state["in_sub_question"] = True
                        sub_question = current_question["sub_question"]
                        line_bot_api.reply_message(
                            event.reply_token,
                            create_flex_message(sub_question["text"], sub_question["options"])
                        )
                        logger.info(f"User {user_id} entered sub-question for question {current_question_idx + 1} for patient ID {patient_id}")
                    else:
                        if "sub_question" in current_question:
                            if (current_question_idx == 0 and user_input == "因行動不便無法洗澡") or \
                               (current_question_idx == 2 and user_input == "因行動不便無法走路") or \
                               (current_question_idx == 12 and user_input == "無法執行"):
                                form_data_scores[user_id].append((f"q{current_question_idx + 1}_b", None))
                            else:
                                form_data_scores[user_id].append((f"q{current_question_idx + 1}_b", 5))
                        state["current_question"] += 1
                        if state["current_question"] < len(questions):
                            next_question = questions[state["current_question"]]
                            line_bot_api.reply_message(
                                event.reply_token,
                                create_flex_message(next_question["text"], next_question["options"])
                            )
                            logger.info(f"User {user_id} moved to question {state['current_question'] + 1} for patient ID {patient_id}")
                        else:
                            show_results(event, user_id, patient_id)
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"請選擇有效選項：{', '.join(current_question['options'])}")
                    )
                    logger.error(f"Invalid question option by user {user_id}: {user_input}")
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="處理問卷時發生錯誤，請重新開始。")
            )
            logger.error(f"Error processing questionnaire for user {user_id}: {e}")
            user_states.pop(user_id, None)
            form_data.pop(user_id, None)
            form_data_scores.pop(user_id, None)
            return

    # 檢查是否為觸發關鍵詞
    if user_input in TRIGGER_KEYWORDS:
        user_states[user_id] = 'selecting_name'
        user_states[user_id + '_pending_action'] = user_input
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請輸入要操作的病患姓名')
        )
        logger.info(f"User {user_id} triggered action {user_input}, asking for patient name")
        return

    # Handle "新增" functionality
    if user_input == '新增':
        user_states[user_id] = 'adding_name'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請輸入您的姓名')
        )
        logger.info(f"User {user_id} started adding new patient")
        return

    # 如果輸入不是關鍵詞，也不是處理中的狀態，回應默認訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='請輸入有效指令，例如「新增」或「查詢資料」。')
    )
    logger.info(f"User {user_id} sent unrecognized input: {user_input}")

def show_results(event, user_id, patient_id):
    if user_id not in form_data or user_id not in form_data_scores:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="錯誤：找不到您的填表資料，請重新嘗試。")
        )
        logger.error(f"No form data or scores for user {user_id}")
        return

    # Extract scores
    score_dict = dict(form_data_scores[user_id])
    logger.info(f"Score dictionary for user {user_id}: {score_dict}")

    # Calculate KCCQ scores with validation
    def rescale(score, divisor):
        if score is None:
            return None
        # Ensure minimum value is 0
        raw_score = max(0, 100 * (score - 1) / divisor)
        return min(100, raw_score)  # Cap at 100

    # KCCQ-PL (Physical Limitation)
    pl_scores = [score_dict.get('q1_b'), score_dict.get('q2_b'), score_dict.get('q3_b')]
    pl_scores = [s for s in pl_scores if s is not None and 0 <= s <= 5]  # Validate score range
    if pl_scores and len(pl_scores) >= 2:
        avg_pl = sum(pl_scores) / len(pl_scores)
        KCCQ_PL = rescale(avg_pl, 4)
    else:
        KCCQ_PL = None
    logger.info(f"KCCQ_PL scores: {pl_scores}, result: {KCCQ_PL}")

    # KCCQ-SF (Symptom Frequency)
    sf_scores = [
        rescale(score_dict.get('q4_a'), 4),
        rescale(score_dict.get('q5_b'), 5),
        rescale(score_dict.get('q6_b'), 5),
        rescale(score_dict.get('q8_b'), 4)
    ]
    sf_scores = [s for s in sf_scores if s is not None]
    KCCQ_SF = sum(sf_scores) / len(sf_scores) if sf_scores and len(sf_scores) >= 2 else None
    logger.info(f"KCCQ_SF scores: {sf_scores}, result: {KCCQ_SF}")

    # KCCQ-QL (Quality of Life)
    ql_scores = [score_dict.get('q9_a'), score_dict.get('q14_a')]
    ql_scores = [s for s in ql_scores if s is not None and 0 <= s <= 5]
    if ql_scores and len(ql_scores) >= 1:
        avg_ql = sum(ql_scores) / len(ql_scores)
        KCCQ_QL = rescale(avg_ql, 4)
    else:
        KCCQ_QL = None
    logger.info(f"KCCQ_QL scores: {ql_scores}, result: {KCCQ_QL}")

    # KCCQ-SL (Social Limitation)
    sl_scores = [score_dict.get('q10_b'), score_dict.get('q11_b'), score_dict.get('q12_b')]
    sl_scores = [s for s in sl_scores if s is not None and 0 <= s <= 5]
    if sl_scores and len(sl_scores) >= 2:
        avg_sl = sum(sl_scores) / len(sl_scores)
        KCCQ_SL = rescale(avg_sl, 4)
    else:
        KCCQ_SL = None
    logger.info(f"KCCQ_SL scores: {sl_scores}, result: {KCCQ_SL}")

    # KCCQ-SUM (Overall Summary)
    sum_scores = [s for s in [KCCQ_PL, KCCQ_SF, KCCQ_QL, KCCQ_SL] if s is not None]
    KCCQ_SUM = sum(sum_scores) / len(sum_scores) if sum_scores and len(sum_scores) >= 1 else None
    logger.info(f"KCCQ_SUM scores: {sum_scores}, result: {KCCQ_SUM}")

    # Categorize the result
    def categorize_score(score):
        if score is None:
            return "無法評估（數據不完整）"
        elif 0 <= score <= 25:
            return "較差"
        elif 26 <= score <= 50:
            return "差"
        elif 51 <= score <= 75:
            return "好"
        elif 76 <= score <= 100:
            return "很好"
        return "無效分數"

    # Prepare result message
    results_text = "\n".join([f"{question}: {answer}" for question, answer in form_data[user_id]])
    kccq_text = f"問卷填寫完成。\n\n每題結果:\n{results_text}\n\nKCCQ 評估結果：\n"
    kccq_text += f"Physical Limitation: {KCCQ_PL:.1f} ({categorize_score(KCCQ_PL)})\n" if KCCQ_PL is not None else "Physical Limitation: 無法計算（數據不完整）\n"
    kccq_text += f"Symptom Frequency: {KCCQ_SF:.1f} ({categorize_score(KCCQ_SF)})\n" if KCCQ_SF is not None else "Symptom Frequency: 無法計算（數據不完整）\n"
    kccq_text += f"Quality of Life: {KCCQ_QL:.1f} ({categorize_score(KCCQ_QL)})\n" if KCCQ_QL is not None else "Quality of Life: 無法計算（數據不完整）\n"
    kccq_text += f"Social Limitation: {KCCQ_SL:.1f} ({categorize_score(KCCQ_SL)})\n" if KCCQ_SL is not None else "Social Limitation: 無法計算（數據不完整）\n"
    kccq_text += f"Overall Summary: {KCCQ_SUM:.1f} ({categorize_score(KCCQ_SUM)})" if KCCQ_SUM is not None else "Overall Summary: 無法計算（數據不完整）"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"Patient ID: {patient_id}\n{kccq_text}")
    )
    logger.info(f"User {user_id} completed questionnaire with KCCQ results for patient ID {patient_id}")

    current_time = dt.now().strftime('%Y-%m-%d %H:%M:%S')
    valid_fields = [
        "q1_a", "q1_b", "q2_a", "q2_b", "q3_a", "q3_b", "q4_a", "q5_a", "q5_b",
        "q6_a", "q6_b", "q7_a", "q7_b", "q8_a", "q8_b", "q9_a", "q10_a", "q10_b",
        "q11_a", "q11_b", "q12_a", "q12_b", "q13_a", "q13_b", "q14_a"
    ]
    score_dict = {field: score for field, score in form_data_scores[user_id] if field in valid_fields}
    fields = ["patient_id", "submission_time"] + valid_fields
    values = [patient_id, current_time] + [score_dict.get(field, None) for field in valid_fields]

    try:
        placeholders = ', '.join(['%s'] * len(fields))
        query = f"INSERT INTO questionnaire_results ({', '.join(fields)}) VALUES ({placeholders})"
        db.insert(query, values)
        logger.info(f"Questionnaire scores saved for patient ID {patient_id}")
    except Exception as e:
        logger.error(f"Error saving questionnaire data for user {user_id}: {e}")

    user_states.pop(user_id, None)
    form_data.pop(user_id, None)
    form_data_scores.pop(user_id, None)
    logger.info(f"Cleared state for user {user_id}")

@app.route('/assets/<path:filename>')
def vite_assets(filename):
    assets_dir = os.path.join(VITE_DIST_DIR, 'assets')
    return send_from_directory(assets_dir, filename)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def vite_index(path):
    if path.startswith('api/'):
        return jsonify({'error': 'API Not Found'}), 404
    index_file = os.path.join(VITE_DIST_DIR, 'index.html')
    return send_from_directory(VITE_DIST_DIR, 'index.html')

if __name__ == "__main__":
    os.makedirs('history', exist_ok=True)
    os.makedirs('photo', exist_ok=True)
    polling_thread = threading.Thread(target=poll_and_notify)
    polling_thread.daemon = True
    polling_thread.start()
    logger.info("Starting Flask application")
    try:
        app.run(host='0.0.0.0', port=5000,debug=False)
        for rule in app.url_map.iter_rules():
            print(rule)
    finally:
        db.close_connection()

