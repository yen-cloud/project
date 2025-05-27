import pymysql
import time

class Database:
    def __init__(self, host, port, user, passwd, database, retries=3):
        self.host = host
        self.port = int(port)
        self.user = user
        self.passwd = passwd
        self.database = database
        self.retries = retries
        self.db = None
        self.connect()

    def connect(self):
        """建立資料庫連線，並重試多次"""
        for attempt in range(self.retries):
            try:
                self.db = pymysql.connect(
                    host=self.host,
                    user=self.user,
                    passwd=self.passwd,
                    database=self.database,
                    port=self.port
                )
                print('連線成功')
                return
            except pymysql.Error as e:
                print(f"連線失敗 (第 {attempt + 1} 次): {e}")
                time.sleep(2)  # 等待 2 秒後重試
        raise Exception("無法連線至資料庫")

    def reconnect(self):
        """檢查連線狀態，如連線已斷則重新連線"""
        if not self.db or not self.db.open:
            print("連線已斷開，嘗試重新連線...")
            self.connect()

    def select(self, sql, params=None):
        """執行查詢並回傳結果"""
        try:
            self.reconnect()
            with self.db.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                return result
        except Exception as e:
            print(f"Error executing select query: {e}")
            return []

    def insert(self, sql, params=None):
        """執行新增資料操作"""
        try:
            self.reconnect()
            with self.db.cursor() as cursor:
                cursor.execute(sql, params)
                self.db.commit()
        except Exception as e:
            print(f"Error executing insert query: {e}")
            self.db.rollback()

    def update(self, sql, params=None):
        """執行更新資料操作"""
        try:
            self.reconnect()
            with self.db.cursor() as cursor:
                cursor.execute(sql, params)
                self.db.commit()
        except Exception as e:
            print(f"Error executing update query: {e}")
            self.db.rollback()
    
    def commit(self):
        """手動提交交易"""
        try:
            self.reconnect()
            self.db.commit()
        except Exception as e:
            print(f"提交交易失敗: {e}")

    def close_connection(self):
        """關閉資料庫連線"""
        try:
            if self.db and self.db.open:
                self.db.close()
                print("連線已關閉")
        except Exception as e:
            print(f"Error closing the connection: {e}")
