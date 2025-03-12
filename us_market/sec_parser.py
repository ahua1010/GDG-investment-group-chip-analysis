import os
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from datetime import datetime
from bs4 import BeautifulSoup
import json
from utils.config import Config

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if pd.isna(obj):
            return None
        if isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d')
        return super().default(obj)

class SECParser:
    @staticmethod
    def process_form4_files(download_dir):
        """處理下載的 Form 4 文件"""
        all_transactions = []
        
        try:
            print(f"\n開始掃描目錄: {download_dir}")
            # 尋找所有 Form 4 XML 文件 (使用新的命名規則)
            files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if f.endswith(".xml")]
            
            print(f"找到 {len(files)} 個 XML 文件")
            
            for file_path in files:
                print(f"\n正在解析文件: {file_path}")
                # 從文件名中提取 ticker
                filename = os.path.basename(file_path)
                ticker = filename.split('_')[1]
                transactions = SECParser._parse_single_file(file_path, ticker)
                if transactions is not None:
                    print(f"成功解析到 {len(transactions)} 筆交易")
                    all_transactions.extend(transactions)
            
            if all_transactions:
                df = pd.DataFrame(all_transactions)
                df = SECParser._process_transactions(df)
                return df
            return None
            
        except Exception as e:
            print(f"Error processing Form 4 files: {str(e)}")
            return None
    
    @staticmethod
    def _parse_single_file(file_path, ticker):
        """解析單個 Form 4 XML 文件"""
        try:
            # 讀取文件內容並檢查
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '<ownershipDocument>' not in content:
                    print(f"文件不包含有效的 XML 標記: {file_path}")
                    return None

            # 使用 ElementTree 解析文件
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
            except ET.ParseError as e:
                print(f"解析 XML 錯誤: {str(e)}")
                # 嘗試修復 XML
                soup = BeautifulSoup(content, 'xml')
                if soup.find('ownershipDocument'):
                    # 取得清理後的 XML 內容
                    clean_xml = str(soup.find('ownershipDocument'))
                    clean_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n{clean_xml}'
                    # 保存修復後的 XML
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(clean_xml)
                    # 重新解析
                    root = ET.fromstring(clean_xml)
                else:
                    print(f"無法修復 XML 文件: {file_path}")
                    return None
            
            # 驗證這是 Form 4 文件
            doc_type = root.find('.//documentType')
            if doc_type is None or doc_type.text.strip() != '4':
                print(f"不是 Form 4 文件: {file_path}")
                return None

            # 獲取報告者信息
            reporter = root.find(".//reportingOwner/reportingOwnerId")
            reporter_name = reporter.find('rptOwnerName').text if reporter is not None else 'Unknown'
            reporter_type = reporter.find('rptOwnerCik').text if reporter is not None else 'Unknown'
            
            # 獲取所有非衍生品交易
            transactions = []
            for transaction in root.findall(".//nonDerivativeTransaction"):
                trans_data = {
                    'ticker': ticker,
                    'reporter_name': reporter_name,
                    'reporter_type': reporter_type,
                    'security_title': transaction.find('.//securityTitle/value').text,
                    'transaction_date': transaction.find('.//transactionDate/value').text,
                    'transaction_code': transaction.find('.//transactionCode').text,
                    'shares': float(transaction.find('.//transactionShares/value').text),
                    'price_per_share': float(transaction.find('.//transactionPricePerShare/value').text),
                    'file_path': file_path,
                    'parsed_date': datetime.now().strftime('%Y-%m-%d')
                }
                
                # 計算交易總值
                trans_data['total_value'] = trans_data['shares'] * trans_data['price_per_share']
                
                # 判斷買入還是賣出
                trans_data['transaction_type'] = 'BUY' if trans_data['transaction_code'] in ['P', 'J'] else 'SELL'
                
                transactions.append(trans_data)
            
            return transactions
            
        except Exception as e:
            print(f"Error parsing file {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def _process_transactions(df):
        """處理交易數據"""
        # 轉換日期格式
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        
        # 添加一些有用的統計
        df['days_since_filing'] = (datetime.now() - df['transaction_date']).dt.days
        
        # 按照交易類型分組計算統計
        summary = df.groupby(['ticker', 'transaction_type']).agg({
            'total_value': 'sum',
            'shares': 'sum',
            'price_per_share': 'mean'
        }).round(2)
        
        print("\nTransaction Summary:")
        print(summary)
        
        return df 

    @staticmethod
    def clean_and_organize_data(df):
        """清理和組織 Form 4 交易數據"""
        try:
            # 1. 轉換日期格式
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            df['filing_date'] = pd.to_datetime(df['filing_date'])
            
            # 2. 按時間排序
            df = df.sort_values('transaction_date')
            
            # 3. 按月份分組
            df['year_month'] = df['transaction_date'].dt.strftime('%Y-%m')
            
            # 4. 添加一些有用的統計
            df['days_since_filing'] = (datetime.now() - df['transaction_date']).dt.days
            
            # 4. 計算每月統計
            monthly_stats = df.groupby(['ticker', 'year_month']).agg({
                'accession_number': 'count'  # 計算每月申報次數
            }).reset_index()
            
            monthly_stats.columns = ['ticker', 'year_month', 'filing_count']
            
            # 5. 清理最終數據集
            final_columns = [
                'ticker',
                'filing_date',
                'transaction_date',
                'form_type',
                'accession_number',
                'year_month',
                'days_since_filing',
                'transaction_type',
                'shares',
                'price_per_share',
                'total_value',
                'BUY',
                'SELL'
            ]
            
            # 確保所有需要的列都存在
            for col in final_columns:
                if col not in df.columns:
                    if col in ['BUY', 'SELL']:
                        df[col] = 0
                    else:
                        df[col] = None
            
            clean_df = df[final_columns].copy()
            
            print("\nMonthly Filing Statistics:")
            print(monthly_stats)
            
            return clean_df, monthly_stats
            
        except Exception as e:
            print(f"Error cleaning data: {str(e)}")
            return None, None
    
    @staticmethod
    def analyze_form4_fund_flow(df):
        """分析 Form 4 資金流向
        
        Args:
            df: Form 4 交易數據框
            
        Returns:
            dict: 包含各種資金流向分析的字典
        """
        try:
            if df is None or df.empty:
                print("沒有 Form 4 交易數據可供分析")
                return None
            
            # 確保必要的欄位存在
            required_columns = ['ticker', 'transaction_date', 'transaction_type', 'shares', 'price_per_share', 'total_value']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"缺少必要的欄位: {missing_columns}")
                
                # 如果缺少 total_value，但有 shares 和 price_per_share，則計算 total_value
                if 'total_value' in missing_columns and 'shares' in df.columns and 'price_per_share' in df.columns:
                    df['total_value'] = df['shares'] * df['price_per_share']
                    missing_columns.remove('total_value')
                
                # 如果缺少 transaction_type，但有 transaction_code，則判斷買入還是賣出
                if 'transaction_type' in missing_columns and 'transaction_code' in df.columns:
                    df['transaction_type'] = df['transaction_code'].apply(
                        lambda x: 'BUY' if x in ['P', 'J'] else 'SELL'
                    )
                    missing_columns.remove('transaction_type')
                
                if missing_columns:
                    print(f"無法繼續分析，仍然缺少必要的欄位: {missing_columns}")
                    return None
            
            # 確保日期欄位是日期類型
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            
            # 添加年月欄位
            if 'year_month' not in df.columns:
                df['year_month'] = df['transaction_date'].dt.strftime('%Y-%m')
            
            # 1. 按公司和交易類型分析資金流向
            company_flow = df.groupby(['ticker', 'transaction_type']).agg({
                'total_value': 'sum',
                'shares': 'sum'
            }).reset_index()
            
            # 2. 按月份分析資金流向
            monthly_flow = df.groupby(['year_month', 'transaction_type']).agg({
                'total_value': 'sum',
                'shares': 'sum'
            }).reset_index()
            
            # 3. 按公司和月份分析資金流向
            company_monthly_flow = df.groupby(['ticker', 'year_month', 'transaction_type']).agg({
                'total_value': 'sum',
                'shares': 'sum'
            }).reset_index()
            
            # 4. 計算淨資金流向 (買入 - 賣出)
            # 創建透視表，按公司和月份分組，計算買入和賣出的總值
            pivot_df = pd.pivot_table(
                df, 
                values='total_value', 
                index=['ticker', 'year_month'], 
                columns='transaction_type', 
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # 確保 BUY 和 SELL 列存在
            if 'BUY' not in pivot_df.columns:
                pivot_df['BUY'] = 0
            if 'SELL' not in pivot_df.columns:
                pivot_df['SELL'] = 0
            
            # 計算淨資金流向
            pivot_df['NET_FLOW'] = pivot_df['BUY'] - pivot_df['SELL']
            
            # 5. 計算累計資金流向
            cumulative_flow = pivot_df.groupby('ticker').agg({
                'BUY': 'sum',
                'SELL': 'sum',
                'NET_FLOW': 'sum'
            }).reset_index()
            
            # 6. 計算每個公司的資金流向趨勢
            # 按公司和日期排序
            trend_df = df.sort_values(['ticker', 'transaction_date'])
            
            # 按公司分組，計算累計資金流向
            trend_data = []
            for ticker, group in trend_df.groupby('ticker'):
                # 按日期排序
                group = group.sort_values('transaction_date')
                
                # 計算每筆交易的資金流向 (買入為正，賣出為負)
                group['flow_value'] = group.apply(
                    lambda row: row['total_value'] if row['transaction_type'] == 'BUY' else -row['total_value'],
                    axis=1
                )
                
                # 計算累計資金流向
                group['cumulative_flow'] = group['flow_value'].cumsum()
                
                # 添加到結果中
                trend_data.append(group[['ticker', 'transaction_date', 'flow_value', 'cumulative_flow']])
            
            if trend_data:
                trend_df = pd.concat(trend_data, ignore_index=True)
            else:
                trend_df = pd.DataFrame()
            
            # 7. 計算內部人信心指標 (買入金額 / 賣出金額)
            confidence_df = cumulative_flow.copy()
            confidence_df['CONFIDENCE'] = np.where(
                confidence_df['SELL'] == 0,
                float('inf'),  # 避免除以零
                confidence_df['BUY'] / confidence_df['SELL']
            )
            
            # 8. 計算最近一個月的資金流向變化
            recent_months = sorted(df['year_month'].unique())[-2:] if len(df['year_month'].unique()) >= 2 else df['year_month'].unique()
            recent_flow = pivot_df[pivot_df['year_month'].isin(recent_months)].copy()
            
            if len(recent_months) >= 2:
                # 計算最近兩個月的資金流向變化
                recent_pivot = pd.pivot_table(
                    recent_flow,
                    values='NET_FLOW',
                    index='ticker',
                    columns='year_month',
                    aggfunc='sum',
                    fill_value=0
                ).reset_index()
                
                # 計算變化率
                recent_pivot['CHANGE'] = recent_pivot[recent_months[1]] - recent_pivot[recent_months[0]]
                recent_pivot['CHANGE_PCT'] = np.where(
                    recent_pivot[recent_months[0]] == 0,
                    float('inf'),
                    recent_pivot['CHANGE'] / recent_pivot[recent_months[0]] * 100
                )
                
                recent_change = recent_pivot[['ticker', 'CHANGE', 'CHANGE_PCT']]
            else:
                recent_change = pd.DataFrame()
            
            return {
                'company_flow': company_flow,
                'monthly_flow': monthly_flow,
                'company_monthly_flow': company_monthly_flow,
                'net_flow': pivot_df,
                'cumulative_flow': cumulative_flow,
                'trend_flow': trend_df,
                'confidence': confidence_df,
                'recent_change': recent_change
            }
            
        except Exception as e:
            print(f"分析 Form 4 資金流向時出錯: {str(e)}")
            return None 

    def analyze_fund_flow(self, transactions_df, save_file=True):
        """分析资金流向
        
        Args:
            transactions_df: 交易数据 DataFrame
            save_file: 是否保存文件
            
        Returns:
            dict: 资金流向分析结果
        """
        try:
            # 获取当前时间戳
            timestamp = datetime.now().strftime('%Y%m%d')
            
            # 按公司统计资金流向
            company_flow = transactions_df.groupby('ticker').agg({
                'BUY': 'sum',
                'SELL': 'sum'
            }).reset_index()
            company_flow['NET_FLOW'] = company_flow['BUY'] - company_flow['SELL']
            
            # 按月统计资金流向
            monthly_flow = transactions_df.groupby(['year_month']).agg({
                'BUY': 'sum',
                'SELL': 'sum'
            }).reset_index()
            monthly_flow['NET_FLOW'] = monthly_flow['BUY'] - monthly_flow['SELL']
            
            # 按公司和月份统计资金流向
            company_monthly_flow = transactions_df.groupby(['ticker', 'year_month']).agg({
                'BUY': 'sum',
                'SELL': 'sum'
            }).reset_index()
            company_monthly_flow['NET_FLOW'] = company_monthly_flow['BUY'] - company_monthly_flow['SELL']
            
            # 计算净资金流向
            net_flow = company_flow.copy()
            
            # 计算累积资金流向
            cumulative_flow = company_flow.copy()
            
            # 计算趋势资金流向
            trend_flow = company_monthly_flow.copy()
            
            # 计算信心指标
            confidence = company_flow.copy()
            confidence['CONFIDENCE'] = confidence['BUY'] / confidence['SELL']
            
            # 保存分析结果
            if save_file:
                # 保存公司资金流向
                company_flow_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_fund_flow_company_flow_{timestamp}.csv"
                )
                company_flow.to_csv(company_flow_file, index=False)
                print(f"Form 4 company_flow 金流分析已保存至: {company_flow_file}")
                
                # 保存月度资金流向
                monthly_flow_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_fund_flow_monthly_flow_{timestamp}.csv"
                )
                monthly_flow.to_csv(monthly_flow_file, index=False)
                print(f"Form 4 monthly_flow 金流分析已保存至: {monthly_flow_file}")
                
                # 保存公司月度资金流向
                company_monthly_flow_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_fund_flow_company_monthly_flow_{timestamp}.csv"
                )
                company_monthly_flow.to_csv(company_monthly_flow_file, index=False)
                print(f"Form 4 company_monthly_flow 金流分析已保存至: {company_monthly_flow_file}")
                
                # 保存净资金流向
                net_flow_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_fund_flow_net_flow_{timestamp}.csv"
                )
                net_flow.to_csv(net_flow_file, index=False)
                print(f"Form 4 net_flow 金流分析已保存至: {net_flow_file}")
                
                # 保存累积资金流向
                cumulative_flow_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_fund_flow_cumulative_flow_{timestamp}.csv"
                )
                cumulative_flow.to_csv(cumulative_flow_file, index=False)
                print(f"Form 4 cumulative_flow 金流分析已保存至: {cumulative_flow_file}")
                
                # 保存趋势资金流向
                trend_flow_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_fund_flow_trend_flow_{timestamp}.csv"
                )
                trend_flow.to_csv(trend_flow_file, index=False)
                print(f"Form 4 trend_flow 金流分析已保存至: {trend_flow_file}")
                
                # 保存信心指标
                confidence_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_fund_flow_confidence_{timestamp}.csv"
                )
                confidence.to_csv(confidence_file, index=False)
                print(f"Form 4 confidence 金流分析已保存至: {confidence_file}")
                
                # 创建资金流向摘要
                flow_summary = pd.DataFrame({
                    'ticker': company_flow['ticker'],
                    'report_date': datetime.now().strftime('%Y-%m-%d'),
                    'filing_count': transactions_df.groupby('ticker').size(),
                    'data_period': f"{min(transactions_df['transaction_date']).strftime('%Y-%m-%d')} to {max(transactions_df['transaction_date']).strftime('%Y-%m-%d')}",
                    'BUY': company_flow['BUY'],
                    'SELL': company_flow['SELL'],
                    'NET_FLOW': company_flow['NET_FLOW'],
                    'CONFIDENCE': confidence['CONFIDENCE']
                })
                
                # 保存资金流向摘要
                flow_summary_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_fund_flow_summary_{timestamp}.csv"
                )
                flow_summary.to_csv(flow_summary_file, index=False)
                print(f"Form 4 资金流向摘要已保存至: {flow_summary_file}")
                
                # 创建综合报告
                report_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_consolidated_report_{timestamp}.xlsx"
                )
                
                with pd.ExcelWriter(report_file) as writer:
                    transactions_df.to_excel(writer, sheet_name='交易明细', index=False)
                    monthly_flow.to_excel(writer, sheet_name='月度统计', index=False)
                    company_flow.to_excel(writer, sheet_name='公司资金流向', index=False)
                    company_monthly_flow.to_excel(writer, sheet_name='公司月度资金流向', index=False)
                    net_flow.to_excel(writer, sheet_name='净资金流向', index=False)
                    cumulative_flow.to_excel(writer, sheet_name='累积资金流向', index=False)
                    trend_flow.to_excel(writer, sheet_name='趋势资金流向', index=False)
                    confidence.to_excel(writer, sheet_name='信心指标', index=False)
                    flow_summary.to_excel(writer, sheet_name='资金流向摘要', index=False)
                
                print(f"综合报告已保存至: {report_file}")
                
                # 创建 JSON 格式报告
                json_data = {
                    'transactions': transactions_df.to_dict(orient='records'),
                    'monthly_flow': monthly_flow.to_dict(orient='records'),
                    'company_flow': company_flow.to_dict(orient='records'),
                    'company_monthly_flow': company_monthly_flow.to_dict(orient='records'),
                    'net_flow': net_flow.to_dict(orient='records'),
                    'cumulative_flow': cumulative_flow.to_dict(orient='records'),
                    'trend_flow': trend_flow.to_dict(orient='records'),
                    'confidence': confidence.to_dict(orient='records'),
                    'flow_summary': flow_summary.to_dict(orient='records')
                }
                
                json_file = os.path.join(
                    Config.US_MARKET_DIR,
                    f"form4_consolidated_report_{timestamp}.json"
                )
                
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=4, cls=CustomJSONEncoder)
                
                print(f"JSON 格式报告已保存至: {json_file}")
            
            return {
                'company_flow': company_flow,
                'monthly_flow': monthly_flow,
                'company_monthly_flow': company_monthly_flow,
                'net_flow': net_flow,
                'cumulative_flow': cumulative_flow,
                'trend_flow': trend_flow,
                'confidence': confidence
            }
            
        except Exception as e:
            print(f"分析资金流向时出错: {str(e)}")
            return None 