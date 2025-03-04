import os
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

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
                'days_since_filing'
            ]
            clean_df = df[final_columns].copy()
            
            print("\nMonthly Filing Statistics:")
            print(monthly_stats)
            
            return clean_df, monthly_stats
            
        except Exception as e:
            print(f"Error cleaning data: {str(e)}")
            return None, None 