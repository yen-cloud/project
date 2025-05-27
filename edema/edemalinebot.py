from flask import Flask, request, abort, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from flask.logging import create_logger
from linebot.models import (
    MessageEvent, TextSendMessage, RichMenu, RichMenuArea, RichMenuSize,
    RichMenuBounds, MessageAction, ImageSendMessage, FlexSendMessage,
    BubbleContainer, BoxComponent, TextComponent, ButtonComponent
)
from SQL import Database
from datetime import datetime as dt, timedelta
import threading
import time
import math
import json
import pygame as pg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask and Line Bot setup
app = Flask(__name__)
LOG = create_logger(app)
line_bot_api = LineBotApi('q3JVzzZMFT3uNo3WExjbE2i90qtTmP1TgdWpPOwPLSg/doEcypG+AR2gKqs+tQm1j1MD/UwNdj/FnaHySWILidNTupCnM10ibKrT4moG2nkjmKHXFwpwJGYWdPlnmwx0PXPXz+NA42UsVC+J/2GfaAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('306e6fd7572e026ee719e1e4eb2ebca6')
ngrok = 'https://29bd-60-250-225-147.ngrok-free.app/'

# Initialize database
db = Database(host='127.0.0.1', port=3306, user='root', passwd='', database='edema2')

@app.route("/", methods=['POST'])
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

def generate_leg_image(IR_list, patient_id):
    try:
        pg.init()
        pg.display.set_mode((900, 600), pg.HIDDEN)
        screen = pg.Surface((900, 600))
        btn_font = pg.font.Font("./font/BAHNSCHRIFT.ttf", 16) if os.path.exists("./font/BAHNSCHRIFT.ttf") else pg.font.SysFont('arial', 16)

        r = 250.0
        transform_rate = 10.0
        valid_points = [(i, float(value)) for i, value in enumerate(IR_list) if value not in [0, None]]

        if len(valid_points) < 3:
            logger.error("Not enough valid points to generate image")
            pg.quit()
            return None

        angle = 360.0 / len(valid_points)
        points = []
        leg_len = []
        current_time = dt.now().strftime("%Y%m%d%H%M")

        for i, value in valid_points:
            actual_len = r - value * transform_rate
            leg_y = actual_len * math.sin(math.radians(i * angle))
            leg_x = actual_len * math.cos(math.radians(i * angle))
            point = (450.0 - leg_y * 0.7, 300.0 - leg_x * 0.7)
            leg_len.append(actual_len)
            points.append(point)

        def calculate_area_and_perimeter(points):
            n = len(points)
            area = 0.0
            perimeter = 0.0
            for i in range(n):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                area += (x1 * y2 - x2 * y1)
                perimeter += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            area = abs(area) / 2.0
            return area, perimeter

        leg_area, leg_size = calculate_area_and_perimeter(points)

        screen.fill((255, 255, 255))
        pg.draw.line(screen, (200, 200, 200), (150, 300), (750, 300), 3)
        pg.draw.line(screen, (200, 200, 200), (450, 50), (450, 550), 3)

        screen.blit(btn_font.render(f"Patient ID: {patient_id}", True, (70, 70, 70)), (50, 50))
        screen.blit(btn_font.render(f"Measurement time: {time.ctime()}", True, (70, 70, 70)), (50, 80))
        screen.blit(btn_font.render(f"Ankle area: {round(leg_area / (transform_rate**2), 1)} cm^2", True, (70, 70, 70)), (50, 110))
        screen.blit(btn_font.render(f"Ankle circumference: {round(leg_size / transform_rate, 1)} cm", True, (70, 70, 70)), (50, 140))

        if len(points) > 2:
            pg.draw.polygon(screen, (255, 200, 200), points, 0)
            pg.draw.polygon(screen, (150, 150, 150), points, 1)

        os.makedirs('photo', exist_ok=True)
        os.makedirs(f'history/{patient_id}', exist_ok=True)
        image_path = f"photo/{current_time}_patient_{patient_id}.png"
        history_path = f"history/{patient_id}/{current_time}_patient_{patient_id}.png"
        pg.image.save(screen, image_path)
        pg.image.save(screen, history_path)
        logger.info(f"Screenshot saved as {image_path} and {history_path}")
        pg.quit()
        return image_path
    except Exception as e:
        logger.error(f"Error generating leg image: {e}")
        pg.quit()
        return None

def poll_and_notify():
    while True:
        try:
            entries = db.select("""
                SELECT p.line_id, f.patient_id, f.measurement_time, f.point, f.point2
                FROM patients p
                JOIN foot_data f ON f.patient_id = p.patient_id
                WHERE f.notified = 1;
            """)

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

                image_path = generate_leg_image(IR_list, patient_id)
                
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
        measurement_time = dt.now().strftime('%Y-%m-d %H:%M:%S')

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
            VALUES (%s, %s, 1, %s, %s);
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

def calculate_area_and_perimeter(points, transform_rate=10.0):
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

    # Current date and time (May 26, 2025, 18:06 PM CST)
    current_time = dt.now()
    two_weeks_ago = current_time - timedelta(days=14)

    # Log the raw history data
    logger.info(f"Raw history data for patient {patient_id}: {history_data}")

    # Convert measurement_time to datetime and filter data
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

    # Log the filtered data
    logger.info(f"Processed data within last 14 days for patient {patient_id}: {processed_data}")

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

        area, perimeter = calculate_area_and_perimeter(points, transform_rate)
        perimeters.append(perimeter)
        areas.append(area)
        logger.info(f"Calculated for {measurement_time}: Area={area}, Perimeter={perimeter}")

    if not times:
        logger.info(f"No valid data points to plot for patient {patient_id}")
        return None

    # Log the final data to plot
    logger.info(f"Final data to plot for patient {patient_id}: Times={times}, Perimeters={perimeters}, Areas={areas}")

    plt.figure(figsize=(10, 6))
    plt.plot(times, perimeters, label='Perimeter (cm)', marker='o')
    plt.plot(times, areas, label='Area (cm²)', marker='s')
    
    plt.title(f'Patient ID: {patient_id}\nFoot Perimeter and Area Over Time')
    plt.xlabel('Measurement Time')
    plt.ylabel('Value')
    plt.legend()
    
    # Set x-axis ticks to only the exact data points
    plt.xticks(ticks=times, labels=[t.strftime('%m-%d %H:%M') for t in times])
    
    # Add grid
    plt.grid(True)
    
    # Annotate values for each point
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
    current_time = dt.now().strftime("%Y%m%d%H%M")
    image_path = f"history/{patient_id}/{current_time}_patient_{patient_id}_linechart.png"
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
                            action={
                                "type": "message",
                                "label": option,
                                "text": option
                            },
                            style='primary',
                            margin='sm'
                        ) for option in options
                    ]
                ),
                ButtonComponent(
                    action={
                        "type": "message",
                        "label": "取消填寫問卷",
                        "text": "取消"
                    },
                    style='secondary',
                    margin='lg'
                )
            ]
        )
    )
    return FlexSendMessage(alt_text='問卷問題', contents=bubble)

questions = [
    {
        "text": "請問你今天是泡澡還是沖澡？",
        "options": ["泡澡", "沖澡", "擦澡", "不想洗澡", "因行動不便無法洗澡"],
        "sub_question": {
            "text": "在你洗澡的過程中是否會覺得累或感到喘？",
            "options": ["非常累或喘", "很累或喘", "相當累或喘", "有點累或喘", "一點都不累或喘"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer in ["泡澡", "沖澡"]
    },
    {
        "text": "有沒有去便利商店散步？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "在走路的過程，是否有覺得累或感到喘？",
            "options": ["非常累或喘", "很累或喘", "相當累或喘", "有點累或喘", "一點都不累或喘"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "有沒有急著去做一件事？",
        "options": ["有", "沒有", "因行動不便無法走路"],
        "sub_question": {
            "text": "在走路的過程，是否有覺得累或感到喘？",
            "options": ["非常累或喘", "很累或喘", "相當累或喘", "有點累或喘", "一點都不累或喘"],
            "scores": [1, 2, 3, 4, 5]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "今天早上起床，你是否有覺得腳部水腫？",
        "options": ["有", "沒有"],
        "scores": [0, 1]
    },
    {
        "text": "昨天有沒有因為疲憊(累)而去影響您去做您想做的事情呢？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "昨天大概有幾次因為疲憊(累)而去影響您去做您想做的事情呢？",
            "options": ["整天都累", "好多次", "1~3次"],
            "scores": [1, 1, 1]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "昨天有沒有因為呼吸急促(喘)而去影響您去做您想做的事情呢？",
        "options": ["有", "沒有"],
        "sub_question": {
            "text": "昨天大概有幾次因為呼吸急促(喘)而去影響您去做您想做的事情呢？",
            "options": ["整天都累", "好多次", "1~3次"],
            "scores": [1, 1, 1]
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
            "scores": [0, 1]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "昨天有沒有因為心臟衰竭的症狀影響您享受生活呢？",
        "options": ["有", "沒有"],
        "scores": [0, 1]
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
            "options": ["嚴重受到影響", "相當受到影響", "中度受到影響", "稍微受到影響", "並沒有受到影響"]
        },
        "sub_question_condition": lambda answer: answer == "有"
    },
    {
        "text": "請問您對目前心臟衰竭治療的改善情況，能不能接受呢？",
        "options": ["一點也不能接受", "大部分不能接受", "尚可接受", "大部分能接受", "完全沒有影響生活"],
        "scores": [1, 2, 3, 4, 5]
    }
]

def get_patient_id(user_id):
    result = db.select("SELECT patient_id FROM patients WHERE line_id = %s;", (user_id,))
    if result:
        return result[0][0]
    logger.error(f"User ID {user_id} not found in database")
    return None

@handler.add(MessageEvent)
def echo(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()
    logger.info(f"Received message from user {user_id}: {user_input}")

    # Handle "新增" functionality
    if user_input == '新增':
        if get_patient_id(user_id):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='您的 Line ID 已綁定病患資料，請使用其他功能。')
            )
            logger.info(f"User {user_id} already linked, cannot add new patient.")
            return
        user_states[user_id] = 'adding_id'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請輸入您的病患 ID（例如：P001）')
        )
        logger.info(f"User {user_id} started adding new patient.")
        return

    elif user_states.get(user_id) == 'adding_id':
        patient_id = user_input
        existing_patient = db.select("SELECT patient_id FROM patients WHERE patient_id = %s;", (patient_id,))
        if existing_patient:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='該病患 ID 已存在，請輸入其他病患 ID。')
            )
            logger.error(f"Patient ID {patient_id} already exists for user {user_id}")
            return
        user_states[user_id] = {'state': 'adding_name', 'patient_id': patient_id}
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請輸入您的姓名')
        )
        logger.info(f"User {user_id} entered patient ID {patient_id}, now adding name.")
        return

    elif isinstance(user_states.get(user_id), dict) and user_states[user_id].get('state') == 'adding_name':
        patient_name = user_input
        patient_id = user_states[user_id]['patient_id']
        try:
            db.insert("""
                INSERT INTO patients (patient_id, line_id, name, height, gender, level, weight)
                VALUES (%s, %s, %s, NULL, NULL, NULL, NULL);
            """, (patient_id, user_id, patient_name))
            db.insert("""
                INSERT INTO patient (patient_id, weight)
                VALUES (%s, NULL);
            """, (patient_id,))
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'病患 ID {patient_id} 和姓名 {patient_name} 已成功新增並綁定您的 Line ID。')
            )
            logger.info(f"User {user_id} added new patient: ID {patient_id}, Name {patient_name}")
            user_states.pop(user_id, None)
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='新增失敗，請稍後重試。')
            )
            logger.error(f"Error adding patient for user {user_id}: {e}")
            user_states.pop(user_id, None)
        return

    user_info = db.select("SELECT patient_id FROM patients WHERE line_id = %s;", (user_id,))

    if not user_info:
        if event.message.type == 'text':
            patient_id = user_input
            patient_data = db.select("SELECT * FROM patients WHERE patient_id = %s;", (patient_id,))

            if patient_data:
                db.update("UPDATE patients SET line_id = %s WHERE patient_id = %s;", (user_id, patient_id))
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(f'您的病患 ID "{patient_id}" 已保存。')
                )
                logger.info(f"Linked user {user_id} to patient ID {patient_id}")
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('未找到該病患 ID，請檢查您的輸入是否正確，或輸入「新增」以新增病患資料。')
                )
                logger.error(f"Patient ID {patient_id} not found")
        return

    patient_id = user_info[0][0]

    if user_input == '查詢資料':
        result = db.select("""
            SELECT name, height, gender, weight, level
            FROM patients p
            WHERE p.patient_id = %s;
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

    elif user_input == '測量歷史':
        patient_id = get_patient_id(user_id)
        if not patient_id:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='無法找到病患ID')
            )
            return

        history_data = db.select("""
            SELECT measurement_time, point, point2
            FROM foot_data
            WHERE patient_id = %s
            ORDER BY measurement_time;
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

    elif user_input == '編輯資料':
        user_states[user_id] = 'editing'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請輸入要編輯的資料(輸入"身高"或"體重")')
        )
        logger.info(f"User {user_id} started editing data")

    elif user_states.get(user_id) == 'editing' and '身高' in user_input:
        user_states[user_id] = 'editing_height'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請輸入要更改的身高(例如: 170)')
        )
        logger.info(f"User {user_id} editing height")

    elif user_states.get(user_id) == 'editing' and '體重' in user_input:
        user_states[user_id] = 'editing_weight'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請輸入要更改的體重(例如: 65)')
        )
        logger.info(f"User {user_id} editing weight")

    elif user_states.get(user_id) == 'editing_height':
        try:
            new_height = float(user_input)
            db.update("UPDATE patients SET height = %s WHERE patient_id = %s;", (new_height, patient_id))
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

    elif user_states.get(user_id) == 'editing_weight':
        try:
            new_weight = float(user_input)
            db.update("UPDATE patients SET weight = %s WHERE patient_id = %s;", (new_weight, patient_id))
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

    elif user_input == '表單填寫':
        user_states[user_id] = {'current_question': 0, 'in_sub_question': False}
        form_data[user_id] = []
        form_data_scores[user_id] = []
        first_question = questions[0]
        line_bot_api.reply_message(
            event.reply_token,
            create_flex_message(first_question["text"], first_question["options"])
        )
        logger.info(f"User {user_id} started questionnaire")
        return

    elif user_input == "取消":
        user_states.pop(user_id, None)
        form_data.pop(user_id, None)
        form_data_scores.pop(user_id, None)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="填寫表單已取消。")
        )
        logger.info(f"User {user_id} cancelled questionnaire")
        return

    # Handle questionnaire responses
    if user_id in user_states and isinstance(user_states[user_id], dict) and 'current_question' in user_states[user_id]:
        state = user_states[user_id]
        current_question_idx = state["current_question"]
        if current_question_idx >= len(questions):
            show_results(event, user_id)
            return

        current_question = questions[current_question_idx]

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
                    logger.info(f"User {user_id} moved to question {state['current_question'] + 1}")
                else:
                    show_results(event, user_id)
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請選擇有效的選項")
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
                    logger.info(f"User {user_id} entered sub-question for question {current_question_idx + 1}")
                else:
                    # If the user does not enter the sub-question, set the sub-question score based on conditions
                    if "sub_question" in current_question:
                        # Exceptions: Q1 (index 0) with "因行動不便無法洗澡", Q3 (index 2) with "因行動不便無法走路", and Q6 (index 5)
                        if (current_question_idx == 0 and user_input == "因行動不便無法洗澡") or \
                           (current_question_idx == 2 and user_input == "因行動不便無法走路") or \
                           (current_question_idx == 5):
                            form_data_scores[user_id].append((f"q{current_question_idx + 1}_b", None))
                        else:
                            # For all other cases, set the sub-question score to 5
                            form_data_scores[user_id].append((f"q{current_question_idx + 1}_b", 5))
                    state["current_question"] += 1
                    if state["current_question"] < len(questions):
                        next_question = questions[state["current_question"]]
                        line_bot_api.reply_message(
                            event.reply_token,
                            create_flex_message(next_question["text"], next_question["options"])
                        )
                        logger.info(f"User {user_id} moved to question {state['current_question'] + 1}")
                    else:
                        show_results(event, user_id)
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請選擇有效的選項")
                )
                logger.error(f"Invalid question option by user {user_id}: {user_input}")

def show_results(event, user_id):
    if user_id not in form_data or user_id not in form_data_scores:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="錯誤：找不到您的填表資料，請重新嘗試。")
        )
        logger.error(f"No form data or scores for user {user_id}")
        return

    # Extract scores
    score_dict = dict(form_data_scores[user_id])

    # Calculate KCCQ scores
    def rescale(score):
        if score is None:
            return None
        return 100 * (score - 1) / 4

    # KCCQ-PL (Physical Limitation)
    pl_scores = [score_dict.get('q1_b'), score_dict.get('q2_b'), score_dict.get('q3_b')]
    pl_scores = [s for s in pl_scores if s is not None]
    KCCQ_PL = 100 * (sum(pl_scores) / 3 - 1) / 4 if pl_scores and len(pl_scores) >= 2 else None

    # KCCQ-SF (Symptom Frequency)
    sf_scores = [score_dict.get('q4_a'), rescale(score_dict.get('q5_b')), rescale(score_dict.get('q6_b')), rescale(score_dict.get('q8_b'))]
    sf_scores = [s for s in sf_scores if s is not None]
    KCCQ_SF = sum(sf_scores) / 4 if sf_scores and len(sf_scores) >= 2 else None

    # KCCQ-QL (Quality of Life)
    ql_scores = [score_dict.get('q9_a'), score_dict.get('q14_a')]
    ql_scores = [s for s in ql_scores if s is not None]
    KCCQ_QL = 100 * (sum(ql_scores) / 2 - 1) / 4 if ql_scores and len(ql_scores) >= 1 else None

    # KCCQ-SL (Social Limitation)
    sl_scores = [score_dict.get('q10_b'), score_dict.get('q11_b'), score_dict.get('q12_b')]
    sl_scores = [s for s in sl_scores if s is not None]
    KCCQ_SL = 100 * (sum(sl_scores) / 3 - 1) / 4 if sl_scores and len(sl_scores) >= 2 else None

    # KCCQ-SUM (Overall Summary)
    sum_scores = [s for s in [KCCQ_PL, KCCQ_SF, KCCQ_QL, KCCQ_SL] if s is not None]
    KCCQ_SUM = sum(sum_scores) / 4 if sum_scores and len(sum_scores) >= 1 else None

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
    patient_id = get_patient_id(user_id)
    results_text = "\n".join([f"{question}: {answer}" for question, answer in form_data[user_id]])
    kccq_text = f"問卷填寫完成。\n\n每題結果:\n{results_text}\n\nKCCQ 評估結果：\n"
    kccq_text += f"Physical Limitation: {KCCQ_PL:.1f} ({categorize_score(KCCQ_PL)})\n" if KCCQ_PL is not None else "Physical Limitation: 無法計算（數據不完整）\n"
    kccq_text += f"Symptom Frequency: {KCCQ_SF:.1f} ({categorize_score(KCCQ_SF)})\n" if KCCQ_SF is not None else "Symptom Frequency: 無法計算（數據不完整）\n"
    kccq_text += f"Quality of Life: {KCCQ_QL:.1f} ({categorize_score(KCCQ_QL)})\n" if KCCQ_QL is not None else "Quality of Life: 無法計算（數據不完整）\n"
    kccq_text += f"Social Limitation: {KCCQ_SL:.1f} ({categorize_score(KCCQ_SL)})\n" if KCCQ_SL is not None else "Social Limitation: 無法計算（數據不完整）\n"
    if not sum_scores:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"Patient ID: {patient_id}\n沒有資料")
        )
        logger.info(f"User {user_id} has no valid KCCQ data")
        patient_id = get_patient_id(user_id)
        if not patient_id:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="錯誤：無法找到您的病患資料，請確認您的帳號。")
            )
            logger.error(f"No patient ID found for user {user_id}")
            return
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
        return
    kccq_text += f"Overall Summary: {KCCQ_SUM:.1f} ({categorize_score(KCCQ_SUM)})"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"Patient ID: {patient_id}\n{kccq_text}")
    )
    logger.info(f"User {user_id} completed questionnaire with KCCQ results")

    patient_id = get_patient_id(user_id)
    if not patient_id:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="錯誤：無法找到您的病患資料，請確認您的帳號。")
        )
        logger.error(f"No patient ID found for user {user_id}")
        return

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

if __name__ == "__main__":
    os.makedirs('history', exist_ok=True)
    os.makedirs('photo', exist_ok=True)
    polling_thread = threading.Thread(target=poll_and_notify)
    polling_thread.daemon = True
    polling_thread.start()
    logger.info("Starting Flask application")
    try:
        app.run(debug=False)
    finally:
        db.close_connection()
