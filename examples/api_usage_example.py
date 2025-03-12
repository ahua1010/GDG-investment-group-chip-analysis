import os
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 设置环境变量
os.environ['SEC_EMAIL'] = 'test@example.com'

from utils.api import InvestmentDataAPI
from us_market.fund_flow import USFundFlow

def example_1_form4_basic():
    """Form 4 基本功能示例"""
    try:
        print("\n=== 示例 1: Form 4 基本功能 ===")
        
        # 初始化 API
        api = InvestmentDataAPI(email="your-email@example.com")
        
        # 获取单个公司的 Form 4 数据
        print("\n1.1 获取 Apple (AAPL) 的 Form 4 数据:")
        form4_data = api.get_us_form4_data(
            tickers=["AAPL"],
            num_filings=5,
            save_file=True
        )
        
        if form4_data:
            # 显示交易记录
            print("\n交易记录:")
            if 'transactions' in form4_data:
                print(form4_data['transactions'])
            
            # 显示月度统计
            print("\n月度统计:")
            if 'monthly_stats' in form4_data:
                print(form4_data['monthly_stats'])
            
            # 显示资金流向分析
            print("\n资金流向分析:")
            if 'fund_flow_analysis' in form4_data:
                for analysis_type, data in form4_data['fund_flow_analysis'].items():
                    print(f"\n{analysis_type}:")
                    print(data)
        
    except Exception as e:
        print(f"运行示例时出错: {str(e)}")

def example_2_form4_fund_flow():
    """Form 4 金流分析示例"""
    try:
        print("\n=== 示例 2: Form 4 金流分析 ===")
        
        # 初始化 API
        api = InvestmentDataAPI(email="your-email@example.com")
        
        # 获取多个公司的 Form 4 数据并分析金流
        print("\n2.1 获取多个公司的 Form 4 数据并分析金流:")
        form4_data = api.get_us_form4_data(
            tickers=["AAPL", "MSFT", "GOOGL"],
            num_filings=5,
            save_file=True,
            analyze_fund_flow=True
        )
        
        if form4_data and 'fund_flow_analysis' in form4_data:
            # 显示累积资金流向
            print("\n累积资金流向:")
            if 'cumulative_flow' in form4_data['fund_flow_analysis']:
                print(form4_data['fund_flow_analysis']['cumulative_flow'])
            
            # 显示内部人信心指标
            print("\n内部人信心指标:")
            if 'confidence' in form4_data['fund_flow_analysis']:
                print(form4_data['fund_flow_analysis']['confidence'])
            
            # 显示近期变化
            print("\n近期变化:")
            if 'recent_change' in form4_data['fund_flow_analysis']:
                print(form4_data['fund_flow_analysis']['recent_change'])
        
    except Exception as e:
        print(f"运行示例时出错: {str(e)}")

def example_3_market_fund_flow():
    """市场资金流向分析示例"""
    try:
        print("\n=== 示例 3: 市场资金流向分析 ===")
        
        # 初始化资金流向分析器
        fund_flow = USFundFlow(email="your-email@example.com")
        
        # 获取多个公司的市场资金流向数据
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        
        # 获取机构持股数据
        for ticker in tickers:
            try:
                print(f"\n获取 {ticker} 的机构持股数据...")
                holdings = fund_flow.get_institutional_holdings(ticker)
                if holdings is not None and not holdings.empty:
                    print(f"{ticker} 机构持股数据:")
                    print(holdings)
                else:
                    print(f"无法获取 {ticker} 的机构持股数据")
            except Exception as e:
                print(f"获取 {ticker} 的机构持股数据时出错: {str(e)}")
        
        # 获取 ETF 资金流向
        print("\n获取 ETF 资金流向数据...")
        etf_flows = fund_flow.get_etf_fund_flows(days=30)
        if etf_flows is not None:
            print("ETF 资金流向数据示例:")
            print(etf_flows.head())
        
        # 获取行业资金流向
        print("\n获取行业资金流向数据...")
        sector_flows = fund_flow.get_sector_fund_flows(days=30)
        if sector_flows is not None:
            print("行业资金流向数据示例:")
            print(sector_flows.head())
            
    except Exception as e:
        print(f"运行示例时出错: {str(e)}")

def example_4_comprehensive_analysis():
    """综合分析示例"""
    try:
        print("\n=== 示例 4: 综合分析 ===")
        
        # 初始化 API
        api = InvestmentDataAPI(email="your-email@example.com")
        
        # 获取综合分析数据
        print("\n4.1 获取综合分析数据:")
        analysis_data = api.get_us_comprehensive_analysis(
            tickers=["AAPL", "MSFT", "GOOGL"],
            num_filings=5,
            days=30,
            save_file=True
        )
        
        if analysis_data:
            # 显示 Form 4 分析结果
            if 'form4_analysis' in analysis_data:
                print("\nForm 4 分析结果:")
                print(analysis_data['form4_analysis'])
            
            # 显示市场资金流向分析结果
            if 'market_fund_flow' in analysis_data:
                print("\n市场资金流向分析结果:")
                print(analysis_data['market_fund_flow'])
            
            # 显示综合评估结果
            if 'comprehensive_evaluation' in analysis_data:
                print("\n综合评估结果:")
                print(analysis_data['comprehensive_evaluation'])
        
    except Exception as e:
        print(f"运行示例时出错: {str(e)}")

def example_5_intermediate_files():
    """中间文件管理示例"""
    try:
        print("\n=== 示例 5: 中间文件管理 ===")
        
        # 初始化 API
        api = InvestmentDataAPI(email="your-email@example.com")
        
        # 不保留中间文件的示例
        print("\n5.1 不保留中间文件的分析:")
        form4_data = api.get_us_form4_data(
            tickers=["AAPL"],
            num_filings=5,
            save_file=True,
            analyze_fund_flow=True,
            keep_intermediate_files=False
        )
        
        # 保留中间文件的示例
        print("\n5.2 保留中间文件的分析:")
        form4_data = api.get_us_form4_data(
            tickers=["AAPL"],
            num_filings=5,
            save_file=True,
            analyze_fund_flow=True,
            keep_intermediate_files=True
        )
        
    except Exception as e:
        print(f"运行示例时出错: {str(e)}")

if __name__ == "__main__":
    try:
        # 运行所有示例
        example_1_form4_basic()
        example_2_form4_fund_flow()
        example_3_market_fund_flow()
        example_4_comprehensive_analysis()
        example_5_intermediate_files()
        
    except Exception as e:
        print(f"运行示例程序时出错: {str(e)}") 