import pandas as pd

class TWDataParser:
    @staticmethod
    def clean_institutional_data(df):
        """清理並轉換三大法人資料格式"""
        try:
            # 重命名欄位為英文
            column_mapping = {
                '證券代號': 'stock_code',
                '證券名稱': 'stock_name',
                '外陸資買進股數': 'foreign_buy',
                '外陸資賣出股數': 'foreign_sell',
                '投信買進股數': 'investment_trust_buy',
                '投信賣出股數': 'investment_trust_sell',
                '自營商買進股數': 'dealer_buy',
                '自營商賣出股數': 'dealer_sell',
                '日期': 'date'
            }
            
            df = df.rename(columns=column_mapping)
            
            # 轉換數值欄位
            numeric_columns = ['foreign_buy', 'foreign_sell', 'investment_trust_buy',
                             'investment_trust_sell', 'dealer_buy', 'dealer_sell']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
            
            return df
            
        except Exception as e:
            print(f"Error cleaning data: {str(e)}")
            return None 