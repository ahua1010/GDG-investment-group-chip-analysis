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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        # 確保下載目錄存在
        os.makedirs(self.save_path, exist_ok=True)
    
    def download_form4(self, ticker, num_filings=10, force_update=False):
        """下載特定公司的 Form 4 文件"""
        try:
            # 首先獲取 CIK 號碼
            cik = self._get_cik(ticker)
            if not cik:
                print(f"Could not find CIK for {ticker}")
                return False
            print(f"找到 {ticker} 的 CIK: {cik}")
            
            # 添加延遲
            time.sleep(1)
            
            # 構建 SEC EDGAR 查詢 URL
            base_url = f"https://www.sec.gov/cgi-bin/browse-edgar"
            params = {
                'CIK': cik,
                'type': '4',
                'count': num_filings,
                'output': 'atom'
            }
            
            # 獲取文件列表
            print(f"正在獲取 {ticker} 的文件列表...")
            response = requests.get(base_url, params=params, headers=self.headers)
            if response.status_code != 200:
                print(f"Error getting filing list for {ticker}: {response.status_code}")
                return False
            
            # 解析 XML 響應
            root = ET.fromstring(response.content)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            print(f"找到 {len(entries)} 個 Form 4 文件")
            
            # 下載每個文件
            downloaded_count = 0
            skipped_count = 0
            failed_count = 0
            
            for i, entry in enumerate(root.findall('{http://www.w3.org/2005/Atom}entry')):
                # 獲取文件的詳細頁面鏈接
                filing_detail = entry.find('{http://www.w3.org/2005/Atom}link').get('href')
                
                # 檢查是否已有該 ticker 的文件
                existing_files = [f for f in os.listdir(self.save_path) 
                                if f.startswith(f"form4_{ticker}_") and f.endswith(".xml")]
                
                # 如果已有足夠數量的文件且不需強制更新，則跳過
                if len(existing_files) >= num_filings and not force_update:
                    print(f"已有 {len(existing_files)} 個 {ticker} 的 Form 4 文件，跳過下載")
                    return True
                
                # 從詳細頁面獲取實際的 Form 4 XML 文件鏈接
                print(f"正在處理文件 {i + 1}/{len(entries)}...")
                detail_response = requests.get(filing_detail, headers=self.headers)
                if detail_response.status_code != 200:
                    print(f"無法獲取詳細頁面: {filing_detail}")
                    failed_count += 1
                    continue
                
                # 從詳細頁面獲取實際的 XML 文件名
                detail_text = detail_response.text
                xml_link = None
                
                # 使用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(detail_text, 'html.parser')
                
                # 尋找頁面中的完整欄位 XML 文件鏈接 (排除 XSL 轉換版本)
                for table in soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = row.find_all('td')
                        for cell in cells:
                            if cell.text and cell.text.strip() == "Complete submission text file":
                                if cell.find_next_sibling('td') and cell.find_next_sibling('td').find('a'):
                                    href = cell.find_next_sibling('td').find('a').get('href', '')
                                    if href:
                                        if not href.startswith('http'):
                                            xml_link = f"https://www.sec.gov{href}"
                                        else:
                                            xml_link = href
                                        print(f"找到完整提交文件: {xml_link}")
                                        break
                
                # 如果找不到完整提交文件，嘗試獲取原始的 XML 文件 (排除 xslF345X05 路徑)
                if not xml_link:
                    for link in soup.find_all('a'):
                        href = link.get('href', '')
                        if '.xml' in href and 'xslF345X05' not in href:
                            if not href.startswith('http'):
                                xml_link = f"https://www.sec.gov{href}"
                            else:
                                xml_link = href
                            print(f"找到原始 XML 文件: {xml_link}")
                            break
                
                if xml_link:
                    # 添加延遲以遵守 SEC 的訪問限制
                    time.sleep(10)
                    if self._download_filing(xml_link, ticker):
                        downloaded_count += 1
                else:
                    print(f"Could not find Form 4 XML link for {ticker}")
                    failed_count += 1
            
            print(f"成功下載 {downloaded_count} 個文件，跳過 {skipped_count} 個文件，失敗 {failed_count} 個文件")
            return downloaded_count > 0
            
        except Exception as e:
            print(f"Error downloading Form 4 for {ticker}: {str(e)}")
            return False
    
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