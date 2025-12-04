# -*- coding: utf-8 -*-
"""
腾讯股票数据接口封装
接口地址: https://qt.gtimg.cn/q=股票代码
"""

import requests
import re
from typing import List, Dict, Optional


class TXStockAPI:
    """腾讯股票数据接口"""
    
    BASE_URL = "https://qt.gtimg.cn/q="
    
    # 数据字段映射（基于腾讯接口返回格式）
    FIELD_MAP = {
        0: "market",           # 市场标识
        1: "name",             # 股票名称
        2: "code",             # 股票代码
        3: "current_price",    # 当前价格
        4: "yesterday_close",  # 昨收价
        5: "today_open",       # 今开价
        6: "volume",           # 成交量（手）
        7: "outer_volume",     # 外盘
        8: "inner_volume",     # 内盘
        9: "buy1_price",       # 买一价
        10: "buy1_volume",     # 买一量
        11: "buy2_price",      # 买二价
        12: "buy2_volume",     # 买二量
        13: "buy3_price",      # 买三价
        14: "buy3_volume",     # 买三量
        15: "buy4_price",      # 买四价
        16: "buy4_volume",     # 买四量
        17: "sell1_price",     # 卖一价
        18: "sell1_volume",    # 卖一量
        19: "sell2_price",     # 卖二价
        20: "sell2_volume",    # 卖二量
        21: "sell3_price",     # 卖三价
        22: "sell3_volume",    # 卖三量
        23: "sell4_price",     # 卖四价
        24: "sell4_volume",    # 卖四量
        30: "datetime",        # 日期时间
        31: "change_amount",   # 涨跌额
        32: "change_percent",  # 涨跌幅(%)
        33: "high",            # 最高价
        34: "low",             # 最低价
        38: "turnover",        # 成交额（万）
        43: "pe_ratio",        # 市盈率
        44: "amplitude",       # 振幅(%)
        45: "market_cap",      # 流通市值（亿）
        46: "total_cap",       # 总市值（亿）
        47: "pb_ratio",        # 市净率
    }
    
    @classmethod
    def format_code(cls, code: str) -> str:
        """
        格式化股票代码，添加市场前缀
        6开头 -> sh (上海)
        0/3开头 -> sz (深圳)
        """
        code = code.strip()
        if code.startswith(('sh', 'sz', 'bj')):
            return code
        if code.startswith('6'):
            return f"sh{code}"
        elif code.startswith(('0', '3')):
            return f"sz{code}"
        elif code.startswith(('4', '8')):
            return f"bj{code}"  # 北交所
        return code
    
    @classmethod
    def get_stock_info(cls, codes: str) -> List[Dict]:
        """
        获取股票信息
        
        Args:
            codes: 股票代码，多个用逗号分隔，如 "sz000858,sh600519"
        
        Returns:
            股票信息列表
        """
        # 格式化代码
        code_list = [cls.format_code(c.strip()) for c in codes.split(',')]
        formatted_codes = ','.join(code_list)
        
        url = f"{cls.BASE_URL}{formatted_codes}"
        
        try:
            response = requests.get(url, timeout=10)
            response.encoding = 'gb2312'
            return cls._parse_response(response.text)
        except Exception as e:
            print(f"获取股票数据失败: {e}")
            return []
    
    @classmethod
    def _parse_response(cls, text: str) -> List[Dict]:
        """解析接口返回的数据"""
        stocks = []
        
        # 匹配每只股票的数据
        pattern = r'v_([^=]+)="([^"]*)"'
        matches = re.findall(pattern, text)
        
        for code, data in matches:
            if not data:
                continue
            
            fields = data.split('~')
            stock_info = {"raw_code": code}
            
            for idx, field_name in cls.FIELD_MAP.items():
                if idx < len(fields):
                    value = fields[idx]
                    # 尝试转换数值
                    if field_name not in ['name', 'code', 'datetime', 'market', 'raw_code']:
                        try:
                            if '.' in value:
                                value = float(value) if value else 0.0
                            else:
                                value = int(value) if value else 0
                        except ValueError:
                            pass
                    stock_info[field_name] = value
            
            stocks.append(stock_info)
        
        return stocks
    
    @classmethod
    def get_single_stock(cls, code: str) -> Optional[Dict]:
        """获取单只股票信息"""
        stocks = cls.get_stock_info(code)
        return stocks[0] if stocks else None


# A股全部股票代码（示例，实际需要完整列表）
# 这里提供一些常用股票用于测试
SAMPLE_STOCKS = [
    "000001",  # 平安银行
    "000002",  # 万科A
    "000858",  # 五粮液
    "600519",  # 贵州茅台
    "600036",  # 招商银行
    "601318",  # 中国平安
    "000333",  # 美的集团
    "002415",  # 海康威视
    "600900",  # 长江电力
    "601012",  # 隆基绿能
]


if __name__ == "__main__":
    # 测试
    api = TXStockAPI()
    result = api.get_stock_info("sz000858,sh600519")
    for stock in result:
        print(f"{stock.get('name')} ({stock.get('code')}): "
              f"现价 {stock.get('current_price')} "
              f"涨跌 {stock.get('change_percent')}%")

