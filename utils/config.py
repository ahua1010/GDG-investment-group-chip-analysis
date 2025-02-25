import os
from pathlib import Path
from datetime import datetime

class Config:
    # 基本目錄設置
    BASE_DIR = Path(__file__).parents[1].absolute()
    
    # 資料目錄
    DATA_DIR = BASE_DIR / 'data'
    
    # 台股相關設置
    TW_MARKET_DIR = DATA_DIR / 'tw_market'
    TW_MARKET_URL = "https://www.twse.com.tw/fund/T86"
    
    # 美股相關設置
    US_MARKET_DIR = DATA_DIR / 'us_market'
    FORM4_DOWNLOAD_DIR = US_MARKET_DIR / 'downloads'
    
    # SEC API 設置
    SEC_EMAIL = os.getenv('SEC_EMAIL')
    
    # 請求設置
    REQUEST_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    REQUEST_DELAY = 3  # 請求延遲（秒）
    
    @classmethod
    def get_user_agent(cls):
        """獲取用戶代理字符串，可用於其他 API 請求"""
        return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) {cls.SEC_EMAIL}"
    
    @staticmethod
    def ensure_directories():
        """確保所有必要目錄存在"""
        directories = [
            Config.DATA_DIR,
            Config.TW_MARKET_DIR,
            Config.US_MARKET_DIR,
            Config.FORM4_DOWNLOAD_DIR
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True) 