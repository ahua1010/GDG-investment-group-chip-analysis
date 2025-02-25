import requests
import pandas as pd
from datetime import datetime, timedelta
import time

class TWInstitutionalInvestors:
    def __init__(self):
        self.base_url = "https://www.twse.com.tw/fund/T86"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def get_daily_data(self, date):
        """獲取特定日期的三大法人買賣超資料"""
        try:
            params = {
                "response": "json",
                "date": date.strftime("%Y%m%d"),
                "selectType": "ALL"
            }
            
            response = requests.get(self.base_url, params=params, headers=self.headers)
            data = response.json()
            
            if data["stat"] != "OK":
                return None
            
            df = pd.DataFrame(data["data"], columns=data["fields"])
            df["日期"] = date.strftime("%Y-%m-%d")
            return df
            
        except Exception as e:
            print(f"Error fetching data for {date}: {str(e)}")
            return None
    
    def get_historical_data(self, start_date, end_date):
        """獲取歷史區間資料"""
        all_data = []
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # 只在工作日抓取
                data = self.get_daily_data(current_date)
                if data is not None:
                    all_data.append(data)
                time.sleep(3)  # 避免請求過於頻繁
            
            current_date += timedelta(days=1)
        
        return pd.concat(all_data) if all_data else None 