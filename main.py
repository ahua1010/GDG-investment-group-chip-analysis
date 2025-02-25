import os
from datetime import datetime, timedelta

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
        
        successful_downloads = []
        print("\n開始下載 Form 4 文件...")
        force_update = False  # 設置為 True 則強制更新所有文件
        for ticker in tickers:
            print(f"\n處理 {ticker} 的 Form 4 文件:")
            if form4_collector.download_form4(ticker, force_update=force_update):
                print(f"{ticker} Form 4 資料下載完成")
                successful_downloads.append(ticker)
            else:
                print(f"警告: {ticker} 的 Form 4 文件下載失敗")
        
        print(f"\n成功下載的股票: {successful_downloads}")
        if successful_downloads:
            # 解析所有下載的文件
            print(f"\n開始解析下載的文件，目錄: {form4_collector.save_path}")
            parser = SECParser()
            transactions_df = parser.process_form4_files(form4_collector.save_path)
            
            if transactions_df is not None:
                # 保存解析結果
                output_file = os.path.join(Config.US_MARKET_DIR, 
                                          f"form4_transactions_{datetime.now().strftime('%Y%m%d')}.csv")
                transactions_df.to_csv(output_file, index=False)
                print(f"\nForm 4 交易數據已保存至: {output_file}")
    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Program terminated with error: {str(e)}") 