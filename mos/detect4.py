import cv2
from ultralytics import YOLO
import os

class Detection:
    def __init__(self, weights='v11best.pt', device='cuda:0'):
        """
        初始化 YOLO 模型（僅載入模型）
        :param weights: 模型權重檔案的路徑
        :param device: 運行裝置（如 'cuda:0' 或 'cpu'）
        """
        self.model = None  # 初始化為空，稍後載入模型
        self.weights = weights
        self.device = device

    def load_model(self):
        """載入 YOLO 模型到指定設備"""
        self.model = YOLO(self.weights)
        self.model.to(self.device)
        print(f"模型已載入，權重檔案：{self.weights}")

    def predict(self, img_path, conf=0.5):
        """
        執行模型預測
        :param img_path: 要推論的影像路徑
        :param conf: 信心閾值
        :return: 預測結果
        """
        if not self.model:
            raise ValueError("模型尚未載入，請先調用 load_model() 方法載入模型。")

        # 執行推論
        results = self.model.predict(source=img_path, conf=conf, save=False)
        return results

    def annotate_image(self, img_path, results, save_path=None, rectangle_thickness=2, text_thickness=1):
        """
        在影像上繪製偵測結果，並返回座標資訊
        :param img_path: 輸入影像的路徑
        :param results: 模型推論結果
        :param save_path: 標註後影像的儲存路徑
        :param rectangle_thickness: 邊界框的線條粗細
        :param text_thickness: 標籤文字的線條粗細
        :return: 標註影像的路徑，帶標註的影像，偵測結果的座標資訊
        """
        # 讀取原始影像
        original_img = cv2.imread(img_path)
        if original_img is None:
            raise ValueError(f"無法讀取影像：{img_path}")

        # 儲存每個物件的座標資訊
        coordinates = []

        # 繪製邊界框
        for result in results:
            for box in result.boxes:
                x_min, y_min, x_max, y_max = map(int, box.xyxy[0])
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                conf_score = box.conf[0]

                # 儲存座標資訊
                coordinates.append({
                    "class_id": class_id,
                    "class_name": class_name,
                    "x_min": x_min,
                    "y_min": y_min,
                    "x_max": x_max,
                    "y_max": y_max
                })

                # 繪製框和標籤
                cv2.rectangle(original_img, (x_min, y_min), (x_max, y_max), (255, 0, 0), rectangle_thickness)
                cv2.putText(original_img, f"{class_name} {conf_score:.2f}",
                            (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), text_thickness)

        # 儲存標註影像（如果指定）
        if save_path:
            cv2.imwrite(save_path, original_img)
            print(f"標註影像已儲存：{save_path}")

        return save_path, original_img, coordinates



    def crop_objects(self, img_path, results, save_dir):
        """
        將偵測到的物體裁切並另存
        :param img_path: 輸入影像的路徑
        :param results: 模型推論結果
        :param save_dir: 裁切圖片的儲存目錄
        """
        # 讀取原始影像
        original_img = cv2.imread(img_path)
        if original_img is None:
            raise ValueError(f"無法讀取影像：{img_path}")

        os.makedirs(save_dir, exist_ok=True)  # 確保儲存目錄存在
        obj_counter = 0

        for result in results:
            for box in result.boxes:
                x_min, y_min, x_max, y_max = map(int, box.xyxy[0])
                class_id = int(box.cls[0])
                class_name = result.names[class_id]

                # 裁切物品
                cropped_img = original_img[y_min:y_max, x_min:x_max]
                save_path = os.path.join(save_dir, f"{class_name}_{obj_counter}.jpg")
                cv2.imwrite(save_path, cropped_img)
                obj_counter += 1

        print(f"裁切完成，共裁切 {obj_counter} 個物品，儲存於：{save_dir}")
        return obj_counter

