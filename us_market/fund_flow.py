import os
import time
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import yfinance as yf
from utils.config import Config

class USFundFlow:
    """美股資金流向數據收集類"""
    
    def __init__(self, email=None):
        """初始化
        
        Args:
            email: 用於 API 請求的電子郵件地址
        """
        self.email = email or Config.SEC_EMAIL
        self.headers = {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) {self.email}',
            'Accept': 'application/json, text/plain, */*',
        }
    
    def get_institutional_holdings(self, ticker, quarters=4):
        """獲取機構持股數據
        
        Args:
            ticker: 股票代碼
            quarters: 要獲取的季度數量
            
        Returns:
            DataFrame: 機構持股數據
        """
        try:
            print(f"獲取 {ticker} 的機構持股數據...")
            
            # 使用 yfinance 獲取機構持股數據
            stock = yf.Ticker(ticker)
            
            # 獲取機構持股
            institutional_holders = stock.institutional_holders
            if institutional_holders is not None:
                institutional_holders['ticker'] = ticker
                institutional_holders['date'] = datetime.now().strftime('%Y-%m-%d')
                print(f"成功獲取 {ticker} 的機構持股數據: {len(institutional_holders)} 條記錄")
                
                # 保存數據
                timestamp = datetime.now().strftime('%Y%m%d')
                output_file = os.path.join(
                    Config.US_MARKET_DIR, 
                    f"{ticker}_institutional_holders_{timestamp}.csv"
                )
                institutional_holders.to_csv(output_file, index=False)
                print(f"機構持股數據已保存至: {output_file}")
                
                return institutional_holders
            else:
                print(f"無法獲取 {ticker} 的機構持股數據")
                return None
            
        except Exception as e:
            print(f"獲取 {ticker} 的機構持股數據時出錯: {str(e)}")
            return None
    
    def get_etf_fund_flows(self, etf_tickers=None, days=30):
        """獲取 ETF 資金流向數據
        
        Args:
            etf_tickers: ETF 代碼列表，默認為 None (使用預設列表)
            days: 要獲取的天數
            
        Returns:
            DataFrame: ETF 資金流向數據
        """
        if etf_tickers is None:
            # 預設 ETF 列表 (主要美股 ETF)
            etf_tickers = [
                'SPY',  # S&P 500 ETF
                'QQQ',  # 納斯達克 100 ETF
                'IWM',  # Russell 2000 ETF
                'DIA',  # 道瓊斯工業平均指數 ETF
                'XLF',  # 金融業 ETF
                'XLK',  # 科技業 ETF
                'XLE',  # 能源業 ETF
                'XLV',  # 醫療保健業 ETF
                'XLI',  # 工業 ETF
                'XLP'   # 必需消費品 ETF
            ]
        
        try:
            print(f"獲取 ETF 資金流向數據...")
            
            all_etf_data = []
            
            for ticker in etf_tickers:
                try:
                    print(f"處理 {ticker} 的資金流向數據...")
                    
                    # 使用 yfinance 獲取 ETF 數據
                    etf = yf.Ticker(ticker)
                    
                    # 獲取歷史價格和成交量
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days)
                    
                    hist = etf.history(start=start_date, end=end_date)
                    
                    if hist.empty:
                        print(f"無法獲取 {ticker} 的歷史數據")
                        continue
                    
                    # 計算資金流向 (價格變化 * 成交量)
                    hist['price_change'] = hist['Close'] - hist['Open']
                    hist['fund_flow'] = hist['price_change'] * hist['Volume']
                    hist['fund_flow_normalized'] = hist['fund_flow'] / hist['Close']
                    
                    # 添加 ETF 代碼
                    hist['ticker'] = ticker
                    
                    # 重置索引，將日期作為列，並移除時區信息
                    hist = hist.reset_index()
                    hist.rename(columns={'index': 'date', 'Date': 'date'}, inplace=True)
                    hist['date'] = hist['date'].dt.tz_localize(None)  # 移除時區信息
                    
                    # 選擇需要的列
                    etf_data = hist[['date', 'ticker', 'Open', 'High', 'Low', 'Close', 
                                     'Volume', 'fund_flow', 'fund_flow_normalized']]
                    
                    all_etf_data.append(etf_data)
                    print(f"成功獲取 {ticker} 的資金流向數據: {len(etf_data)} 條記錄")
                    
                    # 避免請求過於頻繁
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"獲取 {ticker} 的資金流向數據時出錯: {str(e)}")
            
            if all_etf_data:
                # 合併所有 ETF 數據
                etf_flow_df = pd.concat(all_etf_data, ignore_index=True)
                
                # 保存數據
                timestamp = datetime.now().strftime('%Y%m%d')
                output_file = os.path.join(
                    Config.US_MARKET_DIR, 
                    f"etf_fund_flows_{timestamp}.csv"
                )
                etf_flow_df.to_csv(output_file, index=False)
                print(f"ETF 資金流向數據已保存至: {output_file}")
                
                return etf_flow_df
            else:
                print("無法獲取任何 ETF 資金流向數據")
                return None
            
        except Exception as e:
            print(f"獲取 ETF 資金流向數據時出錯: {str(e)}")
            return None
    
    def get_sector_fund_flows(self, days=30):
        """獲取行業板塊資金流向數據
        
        Args:
            days: 要獲取的天數
            
        Returns:
            DataFrame: 行業板塊資金流向數據
        """
        # 主要行業板塊 ETF
        sector_etfs = {
            'XLF': '金融業',
            'XLK': '科技業',
            'XLE': '能源業',
            'XLV': '醫療保健業',
            'XLI': '工業',
            'XLP': '必需消費品',
            'XLY': '非必需消費品',
            'XLB': '原物料',
            'XLU': '公用事業',
            'XLRE': '房地產'
        }
        
        try:
            print(f"獲取行業板塊資金流向數據...")
            
            # 獲取所有行業板塊 ETF 的資金流向
            etf_flow_df = self.get_etf_fund_flows(etf_tickers=list(sector_etfs.keys()), days=days)
            
            if etf_flow_df is None or etf_flow_df.empty:
                print("無法獲取行業板塊資金流向數據")
                return None
            
            # 添加行業名稱
            etf_flow_df['sector'] = etf_flow_df['ticker'].map(sector_etfs)
            
            # 按日期和行業分組計算資金流向
            sector_flow = etf_flow_df.groupby(['date', 'sector']).agg({
                'fund_flow': 'sum',
                'fund_flow_normalized': 'sum',
                'Volume': 'sum',
                'Close': 'mean'
            }).reset_index()
            
            # 保存數據
            timestamp = datetime.now().strftime('%Y%m%d')
            output_file = os.path.join(
                Config.US_MARKET_DIR, 
                f"sector_fund_flows_{timestamp}.csv"
            )
            sector_flow.to_csv(output_file, index=False)
            print(f"行業板塊資金流向數據已保存至: {output_file}")
            
            return sector_flow
            
        except Exception as e:
            print(f"獲取行業板塊資金流向數據時出錯: {str(e)}")
            return None
    
    def get_market_breadth(self, days=30):
        """獲取市場廣度數據 (漲跌家數、成交量等)
        
        Args:
            days: 要獲取的天數
            
        Returns:
            DataFrame: 市場廣度數據
        """
        try:
            print(f"獲取市場廣度數據...")
            
            # 使用 yfinance 獲取主要指數數據
            indices = {
                '^GSPC': 'S&P 500',
                '^NDX': 'NASDAQ 100',
                '^RUT': 'Russell 2000',
                '^DJI': 'Dow Jones'
            }
            
            all_index_data = []
            
            for symbol, name in indices.items():
                try:
                    print(f"處理 {name} 的市場廣度數據...")
                    
                    # 獲取指數數據
                    index = yf.Ticker(symbol)
                    
                    # 獲取歷史價格
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days)
                    
                    hist = index.history(start=start_date, end=end_date)
                    
                    if hist.empty:
                        print(f"無法獲取 {name} 的歷史數據")
                        continue
                    
                    # 計算漲跌幅
                    hist['daily_return'] = hist['Close'].pct_change() * 100
                    
                    # 添加指數信息
                    hist['index_symbol'] = symbol
                    hist['index_name'] = name
                    
                    # 重置索引，將日期作為列
                    hist = hist.reset_index()
                    hist.rename(columns={'index': 'date', 'Date': 'date'}, inplace=True)
                    
                    # 選擇需要的列
                    index_data = hist[['date', 'index_symbol', 'index_name', 'Open', 'High', 'Low', 
                                       'Close', 'Volume', 'daily_return']]
                    
                    all_index_data.append(index_data)
                    print(f"成功獲取 {name} 的市場廣度數據: {len(index_data)} 條記錄")
                    
                    # 避免請求過於頻繁
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"獲取 {name} 的市場廣度數據時出錯: {str(e)}")
            
            if all_index_data:
                # 合併所有指數數據
                market_breadth_df = pd.concat(all_index_data, ignore_index=True)
                
                # 保存數據
                timestamp = datetime.now().strftime('%Y%m%d')
                output_file = os.path.join(
                    Config.US_MARKET_DIR, 
                    f"market_breadth_{timestamp}.csv"
                )
                market_breadth_df.to_csv(output_file, index=False)
                print(f"市場廣度數據已保存至: {output_file}")
                
                return market_breadth_df
            else:
                print("無法獲取任何市場廣度數據")
                return None
            
        except Exception as e:
            print(f"獲取市場廣度數據時出錯: {str(e)}")
            return None 