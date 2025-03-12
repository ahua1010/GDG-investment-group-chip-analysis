import pandas as pd
import os
from datetime import datetime

class FileHandler:
    def __init__(self, base_path="./data"):
        self.base_path = base_path
        self.intermediate_files = []  # 初始化中間文件列表
        self._init_directories()
    
    def _init_directories(self):
        """初始化數據存儲目錄"""
        directories = [
            os.path.join(self.base_path, "tw_market"),
            os.path.join(self.base_path, "us_market")
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def save_tw_data(self, df, date):
        """儲存台股三大法人資料"""
        file_path = os.path.join(
            self.base_path, 
            "tw_market", 
            f"institutional_investors_{date.strftime('%Y%m%d')}.csv"
        )
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        return file_path
    
    def save_form4_data(self, ticker, df):
        """儲存 Form 4 資料"""
        file_path = os.path.join(
            self.base_path,
            "us_market",
            f"form4_{ticker}_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        df.to_csv(file_path, index=False)
        return file_path

    def cleanup_intermediate_files(self):
        """清理中间文件"""
        if self.intermediate_files:
            print(f"清理 {len(self.intermediate_files)} 个中间文件...")
            for file_path in self.intermediate_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"已删除: {file_path}")
                except Exception as e:
                    print(f"删除文件 {file_path} 时出错: {str(e)}")
            
            # 清空列表
            self.intermediate_files = [] 