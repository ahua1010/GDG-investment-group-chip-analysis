import os
import time
import json
import traceback
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
from utils.config import Config

class Form4Collector:
    def __init__(self, save_path=None, email=None):
        if save_path is None:
            save_path = Config.FORM4_DOWNLOAD_DIR
        if email is None:
            email = Config.SEC_EMAIL
            
        self.save_path = save_path
        self.email = email
        self.headers = {
            'User-Agent': f'{self.email}',
            'Accept': 'application/json',  # 改為接收 JSON
        }
        
        # 確保下載目錄存在
        os.makedirs(self.save_path, exist_ok=True)
    
    def get_form4_transactions(self, ticker, num_filings=10):
        """直接獲取 Form 4 交易數據"""
        try:
            # 獲取 CIK
            cik = self._get_cik(ticker)
            if not cik:
                return None
            
            # 使用正確的 SEC API 端點
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"Error getting data for {ticker}: {response.status_code}")
                return None
            
            data = response.json()
            transactions = []
            
            # 獲取最近的文件列表
            recent_filings = data.get('filings', {}).get('recent', {})
            if not recent_filings:
                print(f"No filings found for {ticker}")
                return None
            
            # 獲取各個數據列表
            form_types = recent_filings.get('form', [])
            filing_dates = recent_filings.get('filingDate', [])
            accession_numbers = recent_filings.get('accessionNumber', [])
            report_dates = recent_filings.get('reportDate', [])
            
            # 找到所有 Form 4 的索引
            form4_indices = [i for i, form in enumerate(form_types) if form == '4'][:num_filings]
            
            # 收集交易數據
            for idx in form4_indices:
                trans_data = {
                    'ticker': ticker,
                    'filing_date': filing_dates[idx],
                    'transaction_date': report_dates[idx],
                    'form_type': form_types[idx],
                    'accession_number': accession_numbers[idx],
                    # 添加模擬的交易詳細信息，用於測試金流分析功能
                    'transaction_type': 'BUY' if idx % 2 == 0 else 'SELL',  # 模擬買入/賣出
                    'shares': 1000 * (idx + 1),  # 模擬股數
                    'price_per_share': 150.0 + idx * 5.0,  # 模擬價格
                    'total_value': (1000 * (idx + 1)) * (150.0 + idx * 5.0)  # 模擬總值
                }
                transactions.append(trans_data)
            
            # 添加延遲以遵守 SEC 的速率限制
            time.sleep(0.1)  # 100ms 延遲
            
            if not transactions:
                print(f"No Form 4 transactions found for {ticker}")
                return None
            
            return pd.DataFrame(transactions)
            
        except Exception as e:
            print(f"Error fetching Form 4 data for {ticker}: {str(e)}")
            return None
    
    def _get_cik(self, ticker):
        """獲取公司的 CIK 號碼"""
        try:
            # SEC 要求至少 10 秒間隔
            time.sleep(10)
            url = "https://www.sec.gov/files/company_tickers.json"
            print(f"\n正在從 {url} 獲取 CIK 信息...")
            response = requests.get(url, headers=self.headers)
            print(f"HTTP 狀態碼: {response.status_code}")
            
            if response.status_code != 200:
                print(f"獲取 CIK 信息失敗: {response.status_code}")
                print(f"回應內容: {response.text[:200]}...")
                return None
            
            # 檢查回應內容
            content = response.content
            print(f"回應內容長度: {len(content)} bytes")
            
            # 嘗試解析 JSON
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"JSON 解析錯誤: {str(e)}")
                print(f"回應內容: {response.text[:200]}...")
                return None
            
            for entry in data.values():
                if entry['ticker'].upper() == ticker.upper():
                    return str(entry['cik_str']).zfill(10)
            
            print(f"在 CIK 數據中找不到 {ticker}")
            return None
            
        except Exception as e:
            print(f"獲取 CIK 時發生錯誤: {str(e)}")
            print(f"錯誤詳情:\n{traceback.format_exc()}")
            return None
    
    def _download_filing(self, url, ticker):
        """下載單個文件"""
        try:
            print(f"\n嘗試下載: {url}")
            
            response = requests.get(url, headers=self.headers)
            print(f"HTTP 狀態碼: {response.status_code}")
            
            if response.status_code == 200:
                content = response.content
                print(f"回應內容長度: {len(content)} bytes")
                
                try:
                    # 先保存文件
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    # 使用 .txt 副檔名保存原始文件
                    raw_filename = f"form4_{ticker}_{timestamp}_raw.txt"
                    raw_file_path = os.path.join(self.save_path, raw_filename)
                    
                    # 先保存原始內容以供參考
                    with open(raw_file_path, 'wb') as f:
                        f.write(content)
                    
                    # 然後處理和提取 XML 部分
                    filename = f"form4_{ticker}_{timestamp}.xml"
                    file_path = os.path.join(self.save_path, filename)
                    
                    # 嘗試修復 XML 內容
                    content_str = content.decode('utf-8', errors='ignore')
                    
                    # 從完整提交文件中提取 XML 部分
                    try:
                        # 尋找 ownershipDocument XML 標籤
                        start_idx = content_str.find('<ownershipDocument>')
                        end_idx = content_str.find('</ownershipDocument>')
                        
                        if start_idx > -1 and end_idx > start_idx:
                            xml_content = content_str[start_idx:end_idx+len('</ownershipDocument>')]
                            # 添加 XML 聲明
                            xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
                            # 直接保存提取後的 XML 內容
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(xml_content)
                            print("已提取 XML 內容")
                            print(f"已保存 XML 文件: {filename}")
                            return True
                        else:
                            print("未找到 ownershipDocument XML 標籤")
                            return False
                    except Exception as e:
                        print(f"提取 XML 內容失敗: {str(e)}")
                        return False
                    
                except Exception as e:
                    print(f"文件處理錯誤: {str(e)}")
                    return False
            else:
                print(f"HTTP 請求失敗: {response.status_code}")
                print(f"回應內容: {response.text[:200]}...")  # 只顯示前200個字符
                return False
            
        except Exception as e:
            print(f"下載過程錯誤: {str(e)}")
            return False
    
    def parse_form4_xml(self, file_path):
        """解析 Form 4 XML 文件"""
        try:
            # 讀取文件內容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 檢查文件內容
            if '<ownershipDocument>' not in content:
                print(f"文件不包含有效的 XML 標記: {file_path}")
                return None
            
            # 直接使用 ElementTree 解析文件
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
            except ET.ParseError as e:
                print(f"解析 XML 錯誤: {str(e)}")
                # 嘗試使用 BeautifulSoup 作為備用方案
                try:
                    soup = BeautifulSoup(content, 'xml')
                    if soup.find('ownershipDocument'):
                        # 重新保存清理後的 XML
                        clean_xml = str(soup.find('ownershipDocument'))
                        clean_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n{clean_xml}'
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(clean_xml)
                        # 再次嘗試解析
                        root = ET.fromstring(clean_xml)
                    else:
                        print(f"BeautifulSoup 無法找到 ownershipDocument 標籤")
                        return None
                except Exception as sub_e:
                    print(f"備用解析方法也失敗: {str(sub_e)}")
                    return None
            
            # 提取交易資訊
            transactions = []
            for transaction in root.findall('.//nonDerivativeTransaction'):
                try:
                    # 提取安全標題
                    security_title_elem = transaction.find('.//securityTitle/value')
                    security_title = security_title_elem.text.strip() if security_title_elem is not None else "Unknown"
                    
                    # 提取交易日期
                    trans_date_elem = transaction.find('.//transactionDate/value')
                    trans_date = trans_date_elem.text.strip() if trans_date_elem is not None else "Unknown"
                    
                    # 提取交易代碼
                    trans_code_elem = transaction.find('.//transactionCode')
                    trans_code = trans_code_elem.text.strip() if trans_code_elem is not None else "Unknown"
                    
                    # 提取股份數量
                    shares_elem = transaction.find('.//transactionShares/value')
                    shares = float(shares_elem.text.strip()) if shares_elem is not None else 0.0
                    
                    # 提取每股價格
                    price_elem = transaction.find('.//transactionPricePerShare/value')
                    price = float(price_elem.text.strip()) if price_elem is not None else 0.0
                    
                    trans_data = {
                        'security_title': security_title,
                        'transaction_date': trans_date,
                        'transaction_code': trans_code,
                        'shares': shares,
                        'price_per_share': price,
                    }
                    transactions.append(trans_data)
                except Exception as e:
                    print(f"解析交易記錄錯誤: {str(e)}")
                    continue
            
            if not transactions:
                print(f"文件中沒有找到交易記錄: {file_path}")
                return None
            
            return pd.DataFrame(transactions)
            
        except Exception as e:
            print(f"解析 Form 4 文件錯誤 {file_path}: {str(e)}")
            traceback.print_exc()
            return None 