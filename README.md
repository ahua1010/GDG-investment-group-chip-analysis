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

## 架構說明

```visual-basic
gdg_invest/
│
├── [main.py](http://main.py/)               # 主程式入口點
│
├── utils/                # 公用工具
│   ├── **init**.py
│   ├── [config.py](http://config.py/)         # 集中式配置管理
│   └── file_handler.py   # 檔案處理工具
│
├── taiwan_market/        # 台灣市場相關模組
│   ├── **init**.py
│   └── institutional_investors.py  # 三大法人資料收集
│
├── us_market/           # 美國市場相關模組
│   ├── **init**.py
│   ├── form4_collector.py  # Form 4 檔案下載
│   └── sec_parser.py       # SEC 檔案解析
│
└── data/                # 資料目錄
├── tw_market/       # 台灣市場資料
│   └── .gitkeep
└── us_market/       # 美國市場資料
├── downloads/   # 原始檔案下載目錄
│   └── .gitkeep
└── .gitkeep
```