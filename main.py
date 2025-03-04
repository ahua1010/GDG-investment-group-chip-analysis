import os
from datetime import datetime, timedelta
import pandas as pd

from utils.config import Config
from utils.file_handler import FileHandler
from taiwan_market.institutional_investors import TWInstitutionalInvestors
from us_market.form4_collector import Form4Collector
from us_market.sec_parser import SECParser

def main():
    try:
        # 確保 SEC_EMAIL 環境變量已設置
        if not Config.SEC_EMAIL:
            os.environ['SEC_EMAIL'] = 'your-email@example.com'  # 使用適當的預設郵箱
            Config.SEC_EMAIL = os.getenv('SEC_EMAIL')  # 重新讀取環境變量
        
        # 確保所有必要目錄存在
        Config.ensure_directories()
        
        # 初始化文件處理器
        file_handler = FileHandler()
        
        # 抓取台股三大法人資料
        tw_collector = TWInstitutionalInvestors()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # 抓取最近一週資料
        
        tw_data = tw_collector.get_historical_data(start_date, end_date)
        if tw_data is not None:
            saved_path = file_handler.save_tw_data(tw_data, end_date)
            print(f"台股三大法人資料已保存至: {saved_path}")
        
        # 抓取 Form 4 資料
        form4_collector = Form4Collector(email="test123@gmail.com")
        
        tickers = ["AAPL", "MSFT", "GOOGL"]  # 示例股票
        all_transactions = []
        
        print("開始獲取 Form 4 交易數據...")
        for ticker in tickers:
            print(f"處理 {ticker} 的 Form 4 交易數據:")
            transactions_df = form4_collector.get_form4_transactions(ticker)
            if transactions_df is not None:
                print(f"{ticker} Form 4 資料獲取完成")
                all_transactions.append(transactions_df)
            else:
                print(f"警告: {ticker} 的 Form 4 資料獲取失敗")
        
        if all_transactions:
            # 合併所有交易數據
            transactions_df = pd.concat(all_transactions, ignore_index=True)
            
            # 清理和組織數據
            clean_df, monthly_stats = SECParser.clean_and_organize_data(transactions_df)
            
            # 保存清理後的數據
            clean_output_file = os.path.join(
                Config.US_MARKET_DIR, 
                f"form4_transactions_clean_{datetime.now().strftime('%Y%m%d')}.csv"
            )
            clean_df.to_csv(clean_output_file, index=False)
            
            # 保存月度統計
            monthly_output_file = os.path.join(
                Config.US_MARKET_DIR, 
                f"form4_monthly_stats_{datetime.now().strftime('%Y%m%d')}.csv"
            )
            monthly_stats.to_csv(monthly_output_file, index=False)
    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Program terminated with error: {str(e)}") 