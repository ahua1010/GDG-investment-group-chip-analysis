import sqlite3
from datetime import datetime
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path="market_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化資料庫表格"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 建立台股三大法人表格
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tw_institutional_investors (
                date TEXT,
                stock_code TEXT,
                foreign_buy REAL,
                foreign_sell REAL,
                investment_trust_buy REAL,
                investment_trust_sell REAL,
                dealer_buy REAL,
                dealer_sell REAL,
                PRIMARY KEY (date, stock_code)
            )
        """)
        
        # 建立 Form 4 表格
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sec_form4_transactions (
                ticker TEXT,
                filing_date TEXT,
                transaction_date TEXT,
                security_title TEXT,
                transaction_code TEXT,
                shares REAL,
                price_per_share REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_tw_data(self, df):
        """儲存台股三大法人資料"""
        conn = sqlite3.connect(self.db_path)
        df.to_sql('tw_institutional_investors', conn, if_exists='append', index=False)
        conn.close()
    
    def save_form4_data(self, ticker, df):
        """儲存 Form 4 資料"""
        conn = sqlite3.connect(self.db_path)
        df['ticker'] = ticker
        df['filing_date'] = datetime.now().strftime('%Y-%m-%d')
        df.to_sql('sec_form4_transactions', conn, if_exists='append', index=False)
        conn.close() 