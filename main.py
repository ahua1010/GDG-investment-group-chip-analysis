import os
import argparse
from datetime import datetime

from utils.api import InvestmentDataAPI

def main(args):
    try:
        # 初始化 API
        api = InvestmentDataAPI(
            email=args.email, 
            keep_intermediate_files=args.keep_intermediate_files,
            generate_json=not args.no_json
        )
        
        # 抓取台股三大法人資料
        if args.collect_tw:
            print(f"開始獲取台股三大法人資料 (最近 {args.days} 天)...")
            api.get_tw_institutional_data(days=args.days)
        
        # 抓取美股 Form 4 資料
        if args.collect_us_form4:
            print("開始獲取美股 Form 4 資料...")
            form4_data = api.get_us_form4_data(
                tickers=args.tickers,
                num_filings=args.num_filings,
                consolidated=True,  # 在抓取階段就生成綜合報告
                only_keep_final_report=not args.keep_intermediate_files
            )
            
            # 如果指定了分析 Form 4 金流，則顯示分析結果
            if args.analyze_form4_fund_flow and form4_data and 'fund_flow' in form4_data:
                print("\n===== Form 4 金流分析結果 =====")
                
                # 顯示累計資金流向
                if 'cumulative_flow' in form4_data['fund_flow'] and not form4_data['fund_flow']['cumulative_flow'].empty:
                    print("\n累計資金流向:")
                    print(form4_data['fund_flow']['cumulative_flow'])
                
                # 顯示內部人信心指標
                if 'confidence' in form4_data['fund_flow'] and not form4_data['fund_flow']['confidence'].empty:
                    print("\n內部人信心指標 (買入金額/賣出金額):")
                    print(form4_data['fund_flow']['confidence'][['ticker', 'BUY', 'SELL', 'NET_FLOW', 'CONFIDENCE']])
                
                # 顯示最近變化
                if 'recent_change' in form4_data['fund_flow'] and not form4_data['fund_flow']['recent_change'].empty:
                    print("\n最近資金流向變化:")
                    print(form4_data['fund_flow']['recent_change'])
                
                print("\n注意: 完整的金流分析結果已保存到 Excel 和 JSON 文件中")
        
        # 抓取美股資金流向資料
        if args.collect_us_fund_flow:
            print("開始獲取美股資金流向資料...")
            api.get_us_fund_flow_data(
                tickers=args.tickers,
                days=args.days,
                consolidated=True,  # 在抓取階段就生成綜合報告
                only_keep_final_report=not args.keep_intermediate_files
            )
        
        # 抓取美股綜合資料 (Form 4 + 資金流向)
        if args.collect_us_comprehensive:
            print("開始獲取美股綜合資料 (Form 4 + 資金流向)...")
            api.get_us_comprehensive_data(
                tickers=args.tickers,
                days=args.days,
                num_filings=args.num_filings,
                only_keep_final_report=not args.keep_intermediate_files
            )
        
        # 生成特定股票的摘要報告
        if args.ticker_summary:
            print(f"生成 {args.ticker or '所有股票'} 的摘要報告...")
            api.get_ticker_summary(ticker=args.ticker)
            
    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    # 解析命令行參數
    parser = argparse.ArgumentParser(description='投資數據收集與分析工具')
    
    # 資料收集參數
    parser.add_argument('--collect-tw', action='store_true', help='收集台股三大法人資料')
    parser.add_argument('--collect-us-form4', action='store_true', help='收集美股 Form 4 資料')
    parser.add_argument('--collect-us-fund-flow', action='store_true', help='收集美股資金流向資料')
    parser.add_argument('--collect-us-comprehensive', action='store_true', help='收集美股綜合資料 (Form 4 + 資金流向)')
    parser.add_argument('--days', type=int, default=30, help='收集資料的天數範圍')
    parser.add_argument('--tickers', nargs='+', help='要收集的美股股票代碼列表')
    parser.add_argument('--num-filings', type=int, default=10, help='每個股票收集的 Form 4 文件數量')
    parser.add_argument('--email', type=str, default='your-email@example.com', help='用於 SEC API 的電子郵件地址')
    
    # 分析參數
    parser.add_argument('--analyze-form4-fund-flow', action='store_true', help='分析 Form 4 金流')
    
    # 報告生成參數
    parser.add_argument('--ticker-summary', action='store_true', help='生成股票摘要報告')
    parser.add_argument('--ticker', type=str, help='生成特定股票的摘要報告')
    
    # 文件管理參數
    parser.add_argument('--keep-intermediate-files', action='store_true', help='保留中間文件，默認為 False')
    parser.add_argument('--no-json', action='store_true', help='不生成 JSON 格式的報告，默認為 False')
    
    # 如果沒有參數，預設執行所有功能
    args = parser.parse_args()
    if not any([args.collect_tw, args.collect_us_form4, args.collect_us_fund_flow, 
                args.collect_us_comprehensive, args.ticker_summary]):
        args.collect_tw = True
        args.collect_us_form4 = True
        args.analyze_form4_fund_flow = True  # 預設分析 Form 4 金流
        args.ticker_summary = True
    
    try:
        main(args)
    except Exception as e:
        print(f"Program terminated with error: {str(e)}") 