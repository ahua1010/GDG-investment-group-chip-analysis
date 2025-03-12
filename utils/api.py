import os
import pandas as pd
from datetime import datetime, timedelta
import json

from utils.config import Config
from utils.file_handler import FileHandler
from taiwan_market.institutional_investors import TWInstitutionalInvestors
from us_market.form4_collector import Form4Collector
from us_market.sec_parser import SECParser
from us_market.fund_flow import USFundFlow

# 自定義 JSON 編碼器，處理不可序列化的類型
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, pd.Timedelta):
            return str(obj)
        elif pd.isna(obj):
            return None
        return super().default(obj)

class InvestmentDataAPI:
    """投資數據 API 類，提供簡單的介面供其他程式調用"""
    
    def __init__(self, email=None, keep_intermediate_files=False, generate_json=True):
        """初始化 API
        
        Args:
            email: 用於 SEC API 的電子郵件地址
            keep_intermediate_files: 是否保留中間文件，默認為 False
            generate_json: 是否生成 JSON 格式的報告，默認為 True
        """
        self.email = email or Config.SEC_EMAIL
        self.keep_intermediate_files = keep_intermediate_files
        self.generate_json = generate_json
        self.intermediate_files = []
        
        # 初始化各個模塊
        self.tw_institutional = TWInstitutionalInvestors()
        self.form4_collector = Form4Collector(email=self.email)
        self.sec_parser = SECParser()
        self.us_fund_flow = USFundFlow(email=self.email)
        
        # 確保所有必要目錄存在
        Config.ensure_directories()
        
        # 初始化文件處理器
        self.file_handler = FileHandler()
    
    def _clean_intermediate_files(self):
        """清理中間文件"""
        if not self.keep_intermediate_files and self.intermediate_files:
            print(f"清理 {len(self.intermediate_files)} 個中間文件...")
            for file_path in self.intermediate_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"已刪除: {file_path}")
                except Exception as e:
                    print(f"刪除文件 {file_path} 時出錯: {str(e)}")
            
            # 清空列表
            self.intermediate_files = []
    
    def get_tw_institutional_data(self, days=7, start_date=None, end_date=None, save_file=True):
        """獲取台股三大法人資料
        
        Args:
            days: 要獲取的天數，默認為 7 天
            start_date: 開始日期，如果提供則忽略 days 參數
            end_date: 結束日期，默認為今天
            save_file: 是否保存為文件，默認為 True
            
        Returns:
            DataFrame: 三大法人資料
        """
        tw_collector = TWInstitutionalInvestors()
        
        # 設置日期範圍
        if end_date is None:
            end_date = datetime.now()
        
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        # 獲取資料
        tw_data = tw_collector.get_historical_data(start_date, end_date)
        
        # 保存資料
        if tw_data is not None and save_file:
            saved_path = self.file_handler.save_tw_data(tw_data, end_date)
            print(f"台股三大法人資料已保存至: {saved_path}")
        
        return tw_data
    
    def get_us_form4_data(self, tickers=None, num_filings=10, save_file=True, analyze_fund_flow=False, keep_intermediate_files=None):
        """获取美股 Form 4 数据
        
        Args:
            tickers: 股票代码列表，默认为 ["AAPL", "MSFT", "GOOGL"]
            num_filings: 每个股票获取的文件数量，默认为 10
            save_file: 是否保存为文件，默认为 True
            analyze_fund_flow: 是否分析资金流向，默认为 False
            keep_intermediate_files: 是否保留中间文件，如果为 None 则使用类初始化时的设置
            
        Returns:
            dict: 包含交易数据、月度统计和资金流向分析的字典
        """
        try:
            # 使用类初始化时的设置，除非明确指定
            if keep_intermediate_files is None:
                keep_intermediate_files = self.keep_intermediate_files
            
            if tickers is None:
                tickers = ["AAPL", "MSFT", "GOOGL"]
            
            form4_collector = Form4Collector(email=self.email)
            all_transactions = []
            
            # 获取每个股票的 Form 4 数据
            for ticker in tickers:
                print(f"处理 {ticker} 的 Form 4 交易数据:")
                transactions_df = form4_collector.get_form4_transactions(ticker, num_filings=num_filings)
                if transactions_df is not None:
                    print(f"{ticker} Form 4 数据获取完成")
                    all_transactions.append(transactions_df)
                else:
                    print(f"警告: {ticker} 的 Form 4 数据获取失败")
            
            if not all_transactions:
                return None
            
            # 合并所有交易数据
            transactions_df = pd.concat(all_transactions, ignore_index=True)
            
            # 清理和组织数据
            clean_df, monthly_stats = SECParser.clean_and_organize_data(transactions_df)
            
            # 保存数据
            if save_file:
                timestamp = datetime.now().strftime('%Y%m%d')
                
                # 保存原始清理后的数据
                clean_output_file = os.path.join(
                    Config.US_MARKET_DIR, 
                    f"form4_transactions_clean_{timestamp}.csv"
                )
                clean_df.to_csv(clean_output_file, index=False)
                print(f"Form 4 交易数据已保存至: {clean_output_file}")
                
                # 保存月度统计
                stats_output_file = os.path.join(
                    Config.US_MARKET_DIR, 
                    f"form4_monthly_stats_{timestamp}.csv"
                )
                monthly_stats.to_csv(stats_output_file, index=False)
                print(f"Form 4 月度统计已保存至: {stats_output_file}")
                
                # 添加到中间文件列表
                self.intermediate_files.extend([clean_output_file, stats_output_file])
            
            # 准备返回数据
            form4_data = {
                'transactions': clean_df,
                'monthly_stats': monthly_stats
            }
            
            # 如果需要分析资金流向
            if analyze_fund_flow:
                fund_flow_analysis = self.sec_parser.analyze_fund_flow(
                    clean_df,
                    save_file=save_file
                )
                form4_data['fund_flow_analysis'] = fund_flow_analysis
            
            # 如果不保留中间文件，则清理
            if not keep_intermediate_files:
                self.file_handler.cleanup_intermediate_files()
            
            return form4_data
            
        except Exception as e:
            print(f"获取 Form 4 数据时出错: {str(e)}")
            return None
    
    def get_us_fund_flow_data(self, tickers=None, days=30, save_file=True, consolidated=True, only_keep_final_report=True):
        """獲取美股資金流向數據
        
        Args:
            tickers: 股票代碼列表，默認為 ["AAPL", "MSFT", "GOOGL"]
            days: 要獲取的天數，默認為 30 天
            save_file: 是否保存為文件，默認為 True
            consolidated: 是否生成綜合報告，默認為 True
            only_keep_final_report: 是否只保留最終報告，默認為 True
            
        Returns:
            dict: 包含機構持股、ETF 資金流向、行業板塊資金流向和市場廣度數據的字典
        """
        if tickers is None:
            tickers = ["AAPL", "MSFT", "GOOGL"]
        
        fund_flow = USFundFlow(email=self.email)
        
        # 獲取機構持股數據
        institutional_holdings = {}
        for ticker in tickers:
            print(f"獲取 {ticker} 的機構持股數據...")
            holdings = fund_flow.get_institutional_holdings(ticker)
            if holdings is not None:
                institutional_holdings[ticker] = holdings
        
        # 獲取 ETF 資金流向數據
        print("獲取 ETF 資金流向數據...")
        etf_fund_flows = fund_flow.get_etf_fund_flows(days=days)
        
        # 獲取行業板塊資金流向數據
        print("獲取行業板塊資金流向數據...")
        sector_fund_flows = fund_flow.get_sector_fund_flows(days=days)
        
        # 獲取市場廣度數據
        print("獲取市場廣度數據...")
        market_breadth = fund_flow.get_market_breadth(days=days)
        
        # 生成綜合報告
        if consolidated and save_file:
            timestamp = datetime.now().strftime('%Y%m%d')
            
            # 保存為 Excel 文件
            output_file = os.path.join(
                Config.US_MARKET_DIR, 
                f"us_fund_flow_report_{timestamp}.xlsx"
            )
            
            with pd.ExcelWriter(output_file) as writer:
                # 保存機構持股數據
                for ticker, holdings in institutional_holdings.items():
                    if 'institutional_holders' in holdings and not holdings['institutional_holders'].empty:
                        holdings['institutional_holders'].to_excel(
                            writer, 
                            sheet_name=f'{ticker}_機構持股', 
                            index=False
                        )
                        
                        # 如果需要單獨保存，將文件添加到中間文件列表
                        if save_file and only_keep_final_report:
                            individual_file = os.path.join(
                                Config.US_MARKET_DIR, 
                                f"{ticker}_institutional_holders_{timestamp}.csv"
                            )
                            if os.path.exists(individual_file):
                                self.intermediate_files.append(individual_file)
                    
                    if 'major_holders' in holdings and not holdings['major_holders'].empty:
                        holdings['major_holders'].to_excel(
                            writer, 
                            sheet_name=f'{ticker}_主要持股者', 
                            index=False
                        )
                        
                        # 如果需要單獨保存，將文件添加到中間文件列表
                        if save_file and only_keep_final_report:
                            individual_file = os.path.join(
                                Config.US_MARKET_DIR, 
                                f"{ticker}_major_holders_{timestamp}.csv"
                            )
                            if os.path.exists(individual_file):
                                self.intermediate_files.append(individual_file)
                
                # 保存 ETF 資金流向數據
                if etf_fund_flows is not None:
                    etf_fund_flows.to_excel(writer, sheet_name='ETF資金流向', index=False)
                    
                    # 如果需要單獨保存，將文件添加到中間文件列表
                    if save_file and only_keep_final_report:
                        individual_file = os.path.join(
                            Config.US_MARKET_DIR, 
                            f"etf_fund_flows_{timestamp}.csv"
                        )
                        if os.path.exists(individual_file):
                            self.intermediate_files.append(individual_file)
                
                # 保存行業板塊資金流向數據
                if sector_fund_flows is not None:
                    sector_fund_flows.to_excel(writer, sheet_name='行業板塊資金流向', index=False)
                    
                    # 如果需要單獨保存，將文件添加到中間文件列表
                    if save_file and only_keep_final_report:
                        individual_file = os.path.join(
                            Config.US_MARKET_DIR, 
                            f"sector_fund_flows_{timestamp}.csv"
                        )
                        if os.path.exists(individual_file):
                            self.intermediate_files.append(individual_file)
                
                # 保存市場廣度數據
                if market_breadth is not None:
                    market_breadth.to_excel(writer, sheet_name='市場廣度', index=False)
                    
                    # 如果需要單獨保存，將文件添加到中間文件列表
                    if save_file and only_keep_final_report:
                        individual_file = os.path.join(
                            Config.US_MARKET_DIR, 
                            f"market_breadth_{timestamp}.csv"
                        )
                        if os.path.exists(individual_file):
                            self.intermediate_files.append(individual_file)
            
            print(f"美股資金流向綜合報告已保存至: {output_file}")
            
            # 保存為 JSON 格式
            if self.generate_json:
                json_output_file = os.path.join(
                    Config.US_MARKET_DIR, 
                    f"us_fund_flow_report_{timestamp}.json"
                )
                
                # 將數據轉換為 JSON 格式
                json_data = {
                    'institutional_holdings': {},
                    'etf_fund_flows': etf_fund_flows.to_dict(orient='records') if etf_fund_flows is not None else None,
                    'sector_fund_flows': sector_fund_flows.to_dict(orient='records') if sector_fund_flows is not None else None,
                    'market_breadth': market_breadth.to_dict(orient='records') if market_breadth is not None else None
                }
                
                # 添加機構持股數據
                for ticker, holdings in institutional_holdings.items():
                    json_data['institutional_holdings'][ticker] = {
                        'institutional_holders': holdings['institutional_holders'].to_dict(orient='records') if 'institutional_holders' in holdings and not holdings['institutional_holders'].empty else None,
                        'major_holders': holdings['major_holders'].to_dict(orient='records') if 'major_holders' in holdings and not holdings['major_holders'].empty else None
                    }
                
                with open(json_output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=4, cls=CustomJSONEncoder)
                
                print(f"JSON 格式美股資金流向報告已保存至: {json_output_file}")
            
            # 如果只保留最終報告，清理中間文件
            if only_keep_final_report:
                self._clean_intermediate_files()
        
        return {
            'institutional_holdings': institutional_holdings,
            'etf_fund_flows': etf_fund_flows,
            'sector_fund_flows': sector_fund_flows,
            'market_breadth': market_breadth
        }
    
    def get_us_comprehensive_data(self, tickers=None, days=30, num_filings=10, save_file=True, only_keep_final_report=True):
        """獲取美股綜合數據 (Form 4 + 資金流向)
        
        Args:
            tickers: 股票代碼列表，默認為 ["AAPL", "MSFT", "GOOGL"]
            days: 要獲取的天數，默認為 30 天
            num_filings: 每個股票獲取的 Form 4 文件數量，默認為 10
            save_file: 是否保存為文件，默認為 True
            only_keep_final_report: 是否只保留最終報告，默認為 True
            
        Returns:
            dict: 包含 Form 4 和資金流向數據的字典
        """
        if tickers is None:
            tickers = ["AAPL", "MSFT", "GOOGL"]
        
        # 獲取 Form 4 數據
        print("獲取 Form 4 數據...")
        form4_data = self.get_us_form4_data(
            tickers=tickers,
            num_filings=num_filings,
            save_file=save_file,
            analyze_fund_flow=True,
            keep_intermediate_files=only_keep_final_report
        )
        
        # 獲取資金流向數據
        print("獲取資金流向數據...")
        fund_flow_data = self.get_us_fund_flow_data(
            tickers=tickers,
            days=days,
            save_file=save_file,
            consolidated=True,
            only_keep_final_report=only_keep_final_report
        )
        
        # 生成綜合報告
        if save_file and form4_data is not None and fund_flow_data is not None:
            timestamp = datetime.now().strftime('%Y%m%d')
            
            # 保存為 Excel 文件
            output_file = os.path.join(
                Config.US_MARKET_DIR, 
                f"us_comprehensive_report_{timestamp}.xlsx"
            )
            
            with pd.ExcelWriter(output_file) as writer:
                # Form 4 數據
                if 'transactions' in form4_data and not form4_data['transactions'].empty:
                    form4_data['transactions'].to_excel(writer, sheet_name='Form4_交易明細', index=False)
                
                if 'monthly_stats' in form4_data and not form4_data['monthly_stats'].empty:
                    form4_data['monthly_stats'].to_excel(writer, sheet_name='Form4_月度統計', index=False)
                
                if 'fund_flow_analysis' in form4_data and not form4_data['fund_flow_analysis'].empty:
                    form4_data['fund_flow_analysis'].to_excel(writer, sheet_name='Form4_資金流向分析', index=False)
                
                # 資金流向數據
                # 機構持股數據
                for ticker, holdings in fund_flow_data['institutional_holdings'].items():
                    if 'institutional_holders' in holdings and not holdings['institutional_holders'].empty:
                        holdings['institutional_holders'].to_excel(
                            writer, 
                            sheet_name=f'{ticker}_機構持股', 
                            index=False
                        )
                
                # ETF 資金流向數據
                if 'etf_fund_flows' in fund_flow_data and fund_flow_data['etf_fund_flows'] is not None:
                    fund_flow_data['etf_fund_flows'].to_excel(writer, sheet_name='ETF資金流向', index=False)
                
                # 行業板塊資金流向數據
                if 'sector_fund_flows' in fund_flow_data and fund_flow_data['sector_fund_flows'] is not None:
                    fund_flow_data['sector_fund_flows'].to_excel(writer, sheet_name='行業板塊資金流向', index=False)
                
                # 市場廣度數據
                if 'market_breadth' in fund_flow_data and fund_flow_data['market_breadth'] is not None:
                    fund_flow_data['market_breadth'].to_excel(writer, sheet_name='市場廣度', index=False)
            
            print(f"美股綜合報告已保存至: {output_file}")
            
            # 保存為 JSON 格式
            if self.generate_json:
                json_output_file = os.path.join(
                    Config.US_MARKET_DIR, 
                    f"us_comprehensive_report_{timestamp}.json"
                )
                
                # 將數據轉換為 JSON 格式
                json_data = {
                    'form4_data': {
                        'transactions': form4_data['transactions'].to_dict(orient='records') if 'transactions' in form4_data and not form4_data['transactions'].empty else None,
                        'monthly_stats': form4_data['monthly_stats'].to_dict(orient='records') if 'monthly_stats' in form4_data and not form4_data['monthly_stats'].empty else None,
                        'fund_flow_analysis': form4_data['fund_flow_analysis'].to_dict(orient='records') if 'fund_flow_analysis' in form4_data and not form4_data['fund_flow_analysis'].empty else None
                    },
                    'fund_flow_data': {
                        'institutional_holdings': {},
                        'etf_fund_flows': fund_flow_data['etf_fund_flows'].to_dict(orient='records') if 'etf_fund_flows' in fund_flow_data and fund_flow_data['etf_fund_flows'] is not None else None,
                        'sector_fund_flows': fund_flow_data['sector_fund_flows'].to_dict(orient='records') if 'sector_fund_flows' in fund_flow_data and fund_flow_data['sector_fund_flows'] is not None else None,
                        'market_breadth': fund_flow_data['market_breadth'].to_dict(orient='records') if 'market_breadth' in fund_flow_data and fund_flow_data['market_breadth'] is not None else None
                    }
                }
                
                # 添加機構持股數據
                for ticker, holdings in fund_flow_data['institutional_holdings'].items():
                    json_data['fund_flow_data']['institutional_holdings'][ticker] = {
                        'institutional_holders': holdings['institutional_holders'].to_dict(orient='records') if 'institutional_holders' in holdings and not holdings['institutional_holders'].empty else None,
                        'major_holders': holdings['major_holders'].to_dict(orient='records') if 'major_holders' in holdings and not holdings['major_holders'].empty else None
                    }
                
                with open(json_output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=4, cls=CustomJSONEncoder)
                
                print(f"JSON 格式美股綜合報告已保存至: {json_output_file}")
            
            # 如果只保留最終報告，清理中間文件
            if only_keep_final_report:
                self._clean_intermediate_files()
        
        return {
            'form4_data': form4_data,
            'fund_flow_data': fund_flow_data
        }
    
    def _create_consolidated_analysis(self, transactions_df):
        """創建綜合分析報告
        
        Args:
            transactions_df: 交易數據框
            
        Returns:
            DataFrame: 綜合分析數據框
        """
        if transactions_df.empty:
            return pd.DataFrame()
        
        # 確保日期列是日期類型
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])
        transactions_df['filing_date'] = pd.to_datetime(transactions_df['filing_date'])
        
        # 按公司和月份分組統計
        company_monthly = transactions_df.groupby(['ticker', 'year_month']).agg({
            'accession_number': 'count',
            'transaction_date': ['min', 'max']
        }).reset_index()
        
        # 整理列名
        company_monthly.columns = [
            'ticker', 'year_month', 'filing_count', 
            'first_transaction_date', 'last_transaction_date'
        ]
        
        # 計算每個月的交易天數範圍
        company_monthly['transaction_date_range'] = (
            company_monthly['last_transaction_date'] - company_monthly['first_transaction_date']
        ).dt.days
        
        # 添加最近更新時間
        company_monthly['report_generated_date'] = datetime.now().strftime('%Y-%m-%d')
        
        return company_monthly
    
    def get_ticker_summary(self, ticker=None, save_file=True):
        """生成特定股票的摘要報告
        
        Args:
            ticker: 股票代碼，如果為 None，則生成所有股票的摘要
            save_file: 是否保存為文件，默認為 True
            
        Returns:
            DataFrame: 股票摘要數據框
        """
        # 獲取所有 Form 4 交易數據文件
        transaction_files = [
            os.path.join(Config.US_MARKET_DIR, f) 
            for f in os.listdir(Config.US_MARKET_DIR) 
            if f.startswith("form4_transactions_clean_") and f.endswith(".csv")
        ]
        
        if not transaction_files:
            print("沒有找到 Form 4 交易數據文件")
            return None
        
        # 讀取並合併所有交易數據
        all_transactions = []
        for file in transaction_files:
            df = pd.read_csv(file)
            all_transactions.append(df)
        
        transactions_df = pd.concat(all_transactions, ignore_index=True)
        
        # 去除重複項
        transactions_df = transactions_df.drop_duplicates(
            subset=['ticker', 'filing_date', 'transaction_date', 'accession_number']
        )
        
        if transactions_df.empty:
            return None
        
        # 如果指定了股票代碼，則過濾數據
        if ticker:
            transactions_df = transactions_df[transactions_df['ticker'] == ticker]
            if transactions_df.empty:
                print(f"沒有找到 {ticker} 的交易數據")
                return None
        
        # 確保日期列是日期類型
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])
        
        # 按股票代碼分組統計
        ticker_summary = transactions_df.groupby('ticker').agg({
            'accession_number': 'count',
            'transaction_date': ['min', 'max'],
            'year_month': 'nunique'
        }).reset_index()
        
        # 整理列名
        ticker_summary.columns = [
            'ticker', 'total_filings', 
            'earliest_transaction', 'latest_transaction',
            'months_with_activity'
        ]
        
        # 計算交易活躍度 (每月平均交易次數)
        ticker_summary['activity_level'] = (
            ticker_summary['total_filings'] / ticker_summary['months_with_activity']
        ).round(2)
        
        # 計算數據跨度 (天數)
        ticker_summary['date_range_days'] = (
            ticker_summary['latest_transaction'] - ticker_summary['earliest_transaction']
        ).dt.days
        
        # 添加最近更新時間
        ticker_summary['report_generated_date'] = datetime.now().strftime('%Y-%m-%d')
        
        # 保存為 Excel 文件
        if save_file:
            timestamp = datetime.now().strftime('%Y%m%d')
            
            if ticker:
                output_file = os.path.join(
                    Config.US_MARKET_DIR, 
                    f"form4_{ticker}_summary_{timestamp}.xlsx"
                )
            else:
                output_file = os.path.join(
                    Config.US_MARKET_DIR, 
                    f"form4_all_tickers_summary_{timestamp}.xlsx"
                )
            
            ticker_summary.to_excel(output_file, index=False)
            print(f"股票摘要報告已保存至: {output_file}")
            
            # 保存為 JSON 格式
            if self.generate_json:
                json_output_file = output_file.replace('.xlsx', '.json')
                
                # 將 DataFrame 轉換為字典，然後使用自定義編碼器序列化為 JSON
                with open(json_output_file, 'w', encoding='utf-8') as f:
                    json.dump(ticker_summary.to_dict(orient='records'), f, 
                             cls=CustomJSONEncoder, ensure_ascii=False, indent=4)
                
                print(f"JSON 格式摘要報告已保存至: {json_output_file}")
        
        return ticker_summary
    
    def get_us_comprehensive_analysis(self, tickers, num_filings=10, days=30, save_file=True, keep_intermediate_files=None):
        """获取美股综合分析数据
        
        Args:
            tickers: 股票代码列表
            num_filings: 每个股票要获取的 Form 4 文件数量
            days: 要分析的天数
            save_file: 是否保存文件
            keep_intermediate_files: 是否保留中间文件，如果为 None 则使用类初始化时的设置
            
        Returns:
            dict: 综合分析数据，包含 Form 4 分析、市场资金流向和综合评估
        """
        try:
            # 使用类初始化时的设置，除非明确指定
            if keep_intermediate_files is None:
                keep_intermediate_files = self.keep_intermediate_files
            
            # 获取 Form 4 数据并分析
            form4_data = self.get_us_form4_data(
                tickers=tickers,
                num_filings=num_filings,
                save_file=save_file,
                analyze_fund_flow=True,
                keep_intermediate_files=keep_intermediate_files
            )
            
            # 获取市场资金流向数据
            market_fund_flow = {}
            
            # 获取机构持股数据
            institutional_holdings = {}
            for ticker in tickers:
                try:
                    holdings = self.us_fund_flow.get_institutional_holdings(ticker)
                    if holdings is not None and not holdings.empty:
                        institutional_holdings[ticker] = holdings
                except Exception as e:
                    print(f"获取 {ticker} 的机构持股数据时出错: {str(e)}")
            
            # 获取 ETF 资金流向
            etf_flows = self.us_fund_flow.get_etf_fund_flows(days=days)
            if etf_flows is not None:
                market_fund_flow['etf_fund_flows'] = etf_flows
            
            # 获取行业资金流向
            sector_flows = self.us_fund_flow.get_sector_fund_flows(days=days)
            if sector_flows is not None:
                market_fund_flow['sector_fund_flows'] = sector_flows
            
            # 综合评估
            comprehensive_evaluation = {}
            if form4_data and 'fund_flow_analysis' in form4_data:
                for ticker in tickers:
                    evaluation = {}
                    
                    # Form 4 信心指标
                    if 'confidence' in form4_data['fund_flow_analysis']:
                        confidence_data = form4_data['fund_flow_analysis']['confidence']
                        if not confidence_data.empty:
                            ticker_confidence = confidence_data[confidence_data['ticker'] == ticker]
                            if not ticker_confidence.empty:
                                evaluation['form4_confidence'] = ticker_confidence.iloc[0]['CONFIDENCE']
                    
                    # 机构持股变化
                    if ticker in institutional_holdings:
                        evaluation['institutional_holdings'] = len(institutional_holdings[ticker])
                    
                    # ETF 资金流向
                    if 'etf_fund_flows' in market_fund_flow:
                        etf_data = market_fund_flow['etf_fund_flows']
                        if not etf_data.empty:
                            recent_etf_flow = etf_data.groupby('ticker')['fund_flow_normalized'].mean()
                            evaluation['etf_fund_flow'] = recent_etf_flow.mean()
                    
                    # 行业资金流向
                    if 'sector_fund_flows' in market_fund_flow:
                        sector_data = market_fund_flow['sector_fund_flows']
                        if not sector_data.empty:
                            recent_sector_flow = sector_data.groupby('sector')['fund_flow_normalized'].mean()
                            evaluation['sector_fund_flow'] = recent_sector_flow.mean()
                    
                    comprehensive_evaluation[ticker] = evaluation
            
            # 整合所有数据
            analysis_data = {
                'form4_analysis': form4_data.get('fund_flow_analysis', {}),
                'market_fund_flow': market_fund_flow,
                'comprehensive_evaluation': comprehensive_evaluation
            }
            
            # 如果不保留中间文件，则清理
            if not keep_intermediate_files:
                self.file_handler.cleanup_intermediate_files()
            
            return analysis_data
            
        except Exception as e:
            print(f"获取综合分析数据时出错: {str(e)}")
            return None 