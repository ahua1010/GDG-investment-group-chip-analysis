# 籌碼面分析

這個專案是一個自動化的投資數據收集與分析工具，旨在幫助投資者收集並分析台灣和美國市場的重要投資數據。以下是這個專案的完整功能說明：

## 核心功能

1. 台灣市場資料收集
    - 三大法人資料：自動下載並處理台灣證券交易所的三大法人（外資、投信、自營商）買賣超資料
    - 時間範圍：預設收集最近一週的資料，可調整為其他時間範圍
    - 資料保存：將收集的資料整理為結構化的CSV格式
2. 美國市場 Form 4 資料收集
    - Form 4 文件下載：從美國證券交易委員會(SEC)的EDGAR數據庫自動下載Form 4文件
    - 多公司支援：目前支援Apple(AAPL)、Microsoft(MSFT)、Google(GOOGL)等多家公司的資料收集，可擴展到其他公司
    - 自動化流程：從識別公司CIK碼到獲取文件列表，再到下載和保存，完全自動化
3. Form 4 文件解析與處理
    - 報告人信息（內部人姓名、CIK識別碼）
    - 交易細節（日期、交易代碼、股數、每股價格）
    - 證券類型（普通股、限制性股票單位等）
    - 數據分析：計算關鍵指標如交易總值、交易類型（買入/賣出）等
    - 時間相關性：計算距離交易日的天數等時間指標
4. **Form 4 金流分析**
    - 內部人資金流向：分析內部人買入和賣出的資金流向
    - 公司資金流向：按公司分析內部人交易的資金流向
    - 月度資金流向：按月份分析內部人交易的資金流向
    - 淨資金流向：計算買入減去賣出的淨資金流向
    - 累計資金流向：計算累計的資金流向
    - 內部人信心指標：計算買入金額與賣出金額的比率
    - 資金流向趨勢：分析資金流向的時間趨勢
5. **美股資金流向分析**
    - 機構持股分析：分析機構投資者的持股情況
    - ETF 資金流向：分析主要 ETF 的資金流向
    - 行業板塊資金流向：分析各行業板塊的資金流向
    - 市場廣度數據：分析市場整體的漲跌情況
6. **API 介面**
    - 提供簡單的 API 介面，方便其他程式調用
    - 在資料抓取階段就進行整合，生成綜合報告
    - 支援 JSON 格式輸出，便於與其他系統整合
    - 提供多種報告格式：Excel、CSV、JSON
7. **文件管理**
    - 自動清理中間文件，只保留最終報告
    - 可選擇保留所有中間文件，方便調試
    - 減少磁盤空間佔用，保持數據目錄整潔

## 架構說明

```visual-basic
gdg_invest/
│
├── main.py               # 主程式入口點
│
├── utils/                # 公用工具
│   ├── __init__.py
│   ├── config.py         # 集中式配置管理
│   ├── file_handler.py   # 檔案處理工具
│   ├── database.py       # 數據庫管理
│   └── api.py            # API 介面
│
├── taiwan_market/        # 台灣市場相關模組
│   ├── __init__.py
│   ├── institutional_investors.py  # 三大法人資料收集
│   └── data_parser.py    # 數據解析
│
├── us_market/           # 美國市場相關模組
│   ├── __init__.py
│   ├── form4_collector.py  # Form 4 檔案下載
│   ├── sec_parser.py       # SEC 檔案解析
│   └── fund_flow.py        # 資金流向分析
│
├── examples/            # 示例代碼
│   ├── __init__.py
│   └── api_usage_example.py  # API 使用示例
│
└── data/                # 資料目錄
    ├── tw_market/       # 台灣市場資料
    │   └── .gitkeep
    └── us_market/       # 美國市場資料
        ├── downloads/   # 原始檔案下載目錄
        │   └── .gitkeep
        └── .gitkeep
```

## 使用方法

### 命令行使用

```bash
# 收集台股三大法人資料
python main.py --collect-tw --days 7

# 收集美股 Form 4 資料
python main.py --collect-us-form4 --tickers AAPL MSFT GOOGL --num-filings 10

# 收集美股 Form 4 資料並分析金流
python main.py --collect-us-form4 --analyze-form4-fund-flow --tickers AAPL MSFT GOOGL

# 收集美股資金流向資料
python main.py --collect-us-fund-flow --tickers AAPL MSFT GOOGL --days 30

# 收集美股綜合資料 (Form 4 + 資金流向)
python main.py --collect-us-comprehensive --tickers AAPL MSFT GOOGL

# 生成特定股票的摘要報告
python main.py --ticker-summary --ticker AAPL

# 保留所有中間文件（用於調試）
python main.py --collect-us-comprehensive --keep-intermediate-files

# 不生成 JSON 格式的報告（只生成 Excel 格式）
python main.py --collect-us-comprehensive --no-json

# 執行所有功能
python main.py
```

### API 使用

```python
from utils.api import InvestmentDataAPI

# 初始化 API（默認不保留中間文件）
api = InvestmentDataAPI(email="your-email@example.com")

# 初始化 API（保留中間文件）
api = InvestmentDataAPI(email="your-email@example.com", keep_intermediate_files=True)

# 初始化 API（不生成 JSON 格式的報告）
api = InvestmentDataAPI(email="your-email@example.com", generate_json=False)

# 獲取台股三大法人資料
tw_data = api.get_tw_institutional_data(days=7)

# 獲取美股 Form 4 資料並分析金流
form4_data = api.get_us_form4_data(
    tickers=["AAPL", "MSFT", "GOOGL"],
    num_filings=10,
    consolidated=True,
    only_keep_final_report=True  # 只保留最終報告
)

# 分析 Form 4 金流
if 'fund_flow' in form4_data:
    # 獲取累計資金流向
    cumulative_flow = form4_data['fund_flow']['cumulative_flow']
    
    # 獲取內部人信心指標
    confidence = form4_data['fund_flow']['confidence']
    
    # 獲取最近變化
    recent_change = form4_data['fund_flow']['recent_change']

# 獲取美股資金流向資料
fund_flow_data = api.get_us_fund_flow_data(
    tickers=["AAPL", "MSFT", "GOOGL"],
    days=30,
    only_keep_final_report=True  # 只保留最終報告
)

# 獲取美股綜合資料 (Form 4 + 資金流向)
comprehensive_data = api.get_us_comprehensive_data(
    tickers=["AAPL", "MSFT", "GOOGL"],
    only_keep_final_report=True  # 只保留最終報告
)

# 生成特定股票的摘要報告
ticker_summary = api.get_ticker_summary(ticker="AAPL")
```

更多示例請參考 `examples/api_usage_example.py`。

## 報告格式

### 1. Form 4 交易清單報告

包含以下欄位：
- 股票代碼 (ticker)
- 申報日期 (filing_date)
- 交易日期 (transaction_date)
- 表格類型 (form_type)
- 登記號碼 (accession_number)
- 年月 (year_month)
- 距今天數 (days_since_filing)

### 2. Form 4 月度統計報告

包含以下欄位：
- 股票代碼 (ticker)
- 年月 (year_month)
- 申報次數 (filing_count)

### 3. Form 4 綜合分析報告

包含以下欄位：
- 股票代碼 (ticker)
- 年月 (year_month)
- 申報次數 (filing_count)
- 首次交易日期 (first_transaction_date)
- 最後交易日期 (last_transaction_date)
- 交易日期範圍 (transaction_date_range)
- 報告生成日期 (report_generated_date)

### 4. Form 4 金流分析報告

包含多個分析表：

#### 4.1 公司資金流向 (company_flow)
- 股票代碼 (ticker)
- 交易類型 (transaction_type)：BUY 或 SELL
- 總金額 (total_value)
- 總股數 (shares)

#### 4.2 月度資金流向 (monthly_flow)
- 年月 (year_month)
- 交易類型 (transaction_type)
- 總金額 (total_value)
- 總股數 (shares)

#### 4.3 淨資金流向 (net_flow)
- 股票代碼 (ticker)
- 年月 (year_month)
- 買入金額 (BUY)
- 賣出金額 (SELL)
- 淨資金流向 (NET_FLOW)

#### 4.4 累計資金流向 (cumulative_flow)
- 股票代碼 (ticker)
- 累計買入金額 (BUY)
- 累計賣出金額 (SELL)
- 累計淨資金流向 (NET_FLOW)

#### 4.5 內部人信心指標 (confidence)
- 股票代碼 (ticker)
- 買入金額 (BUY)
- 賣出金額 (SELL)
- 淨資金流向 (NET_FLOW)
- 信心指標 (CONFIDENCE)：買入金額 / 賣出金額

#### 4.6 最近變化 (recent_change)
- 股票代碼 (ticker)
- 變化量 (CHANGE)
- 變化百分比 (CHANGE_PCT)

### 5. 美股資金流向報告

包含多個分析表：

#### 5.1 機構持股 (institutional_holders)
- 股票代碼 (ticker)
- 機構名稱 (Holder)
- 持股數量 (Shares)
- 持股日期 (Date Reported)
- 持股比例 (% Out)
- 持股價值 (Value)

#### 5.2 ETF 資金流向 (etf_fund_flows)
- 日期 (date)
- ETF 代碼 (ticker)
- 開盤價 (Open)
- 最高價 (High)
- 最低價 (Low)
- 收盤價 (Close)
- 成交量 (Volume)
- 資金流向 (fund_flow)
- 標準化資金流向 (fund_flow_normalized)

#### 5.3 行業板塊資金流向 (sector_fund_flows)
- 日期 (date)
- 行業 (sector)
- 資金流向 (fund_flow)
- 標準化資金流向 (fund_flow_normalized)
- 成交量 (Volume)
- 收盤價 (Close)

#### 5.4 市場廣度 (market_breadth)
- 日期 (date)
- 指數代碼 (index_symbol)
- 指數名稱 (index_name)
- 開盤價 (Open)
- 最高價 (High)
- 最低價 (Low)
- 收盤價 (Close)
- 成交量 (Volume)
- 日漲跌幅 (daily_return)

## 依賴套件

- pandas
- numpy
- requests
- beautifulsoup4
- lxml
- openpyxl
- yfinance