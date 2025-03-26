import sqlite3
import time

class Database:
    def __init__(self, db_path, retries=3):
        self.db_path = db_path
        self.retries = retries
        self.db = None
        self.connect()
        # 啟用外鍵約束
        self.db.execute("PRAGMA foreign_keys = ON;")

    def connect(self):
        """連接到資料庫"""
        attempt = 0
        while attempt < self.retries:
            try:
                self.db = sqlite3.connect(self.db_path)
                return
            except sqlite3.Error as e:
                attempt += 1
                if attempt == self.retries:
                    raise Exception(f"Failed to connect to database after {self.retries} attempts: {e}")
                time.sleep(1)

    def select(self, query, params=()):
        """執行 SELECT 查詢"""
        conn = sqlite3.connect(self.db_path)  # 為每次查詢創建新連線
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.commit()
            return result
        except sqlite3.Error as e:
            raise Exception(f"Error executing select query: {e}")
        finally:
            conn.close()

    def insert(self, query, params=()):
        """執行 INSERT 查詢"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Error executing insert query: {e}")
        finally:
            conn.close()

    def update(self, query, params=()):
        """執行 UPDATE 查詢"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Error executing update query: {e}")
        finally:
            conn.close()

    def commit(self):
        """提交變更"""
        if self.db:
            self.db.commit()

    def rollback(self):
        """回滾變更"""
        if self.db:
            self.db.rollback()

    def close(self):
        """關閉連線"""
        if self.db:
            self.db.close()