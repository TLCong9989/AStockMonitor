# -*- coding: utf-8 -*-
"""
A股全市场涨跌统计接口
使用腾讯接口 https://qt.gtimg.cn/q= 获取实时数据
"""

import requests
import re
from typing import Dict, List, Optional
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class MarketStatsAPI:
    """A股全市场统计接口 - 使用腾讯数据源"""
    
    TX_URL = "https://qt.gtimg.cn/q="
    
    # A股股票代码缓存
    _stock_codes = []
    _codes_loaded = False
    
    @classmethod
    def get_all_stock_codes(cls) -> List[str]:
        """获取A股所有股票代码"""
        if cls._codes_loaded and cls._stock_codes:
            return cls._stock_codes
        
        codes = []
        
        # 沪市主板: 600000-609999, 688000-689999(科创板)
        for i in range(600000, 610000):
            codes.append(f"sh{i}")
        for i in range(688000, 690000):
            codes.append(f"sh{i}")
            
        # 深市: 000001-003999(主板), 300000-309999(创业板)
        for i in range(1, 4000):
            codes.append(f"sz{i:06d}")
        for i in range(300000, 310000):
            codes.append(f"sz{i}")
            
        # 北交所: 430000-439999, 830000-839999, 870000-879999
        for i in range(430000, 440000):
            codes.append(f"bj{i}")
        for i in range(830000, 840000):
            codes.append(f"bj{i}")
        for i in range(870000, 880000):
            codes.append(f"bj{i}")
        
        cls._stock_codes = codes
        cls._codes_loaded = True
        return codes
    
    @classmethod
    def get_market_stats(cls) -> Optional[Dict]:
        """
        获取A股全市场涨跌统计 + 上证指数
        """
        try:
            # 并行获取: 全市场统计 + 上证指数
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_stats = executor.submit(cls._get_all_stocks_stats)
                future_index = executor.submit(cls._get_shanghai_index)
                
                stats = future_stats.result()
                index_data = future_index.result()
                
                if stats and index_data:
                    stats.update(index_data)
                    return stats
            return None
            
        except Exception as e:
            print(f"获取市场统计失败: {e}")
            return None

    @classmethod
    def _get_shanghai_index(cls) -> Dict:
        """获取上证指数数据"""
        try:
            url = f"{cls.TX_URL}sh000001"
            resp = requests.get(url, timeout=5)
            # v_sh000001="1~上证指数~000001~3031.23~3027.33~3027.33~..."
            # 3:当前, 4:昨收, 31:涨跌额, 32:涨跌幅
            data = resp.text
            match = re.search(r'v_sh000001="([^"]*)"', data)
            if match:
                fields = match.group(1).split('~')
                if len(fields) > 37:
                    return {
                        'sh_price': float(fields[3]),
                        'sh_pre_close': float(fields[4]),
                        'sh_change': float(fields[31]),
                        'sh_pct': float(fields[32]),
                        'sh_amount': float(fields[37])  # 成交额（万）
                    }
            return {}
        except Exception as e:
            print(f"获取上证指数失败: {e}")
            return {}

    @classmethod
    def _get_all_stocks_stats(cls) -> Optional[Dict]:
        """获取全市场个股统计（原逻辑）"""
        try:
            all_codes = cls.get_all_stock_codes()
            
            # 统计结果
            stats = {
                'up_count': 0,
                'down_count': 0,
                'flat_count': 0,
                'up_3pct': 0,
                'down_3pct': 0,
                'up_5pct': 0,
                'down_5pct': 0,
                'limit_up': 0,
                'limit_down': 0,
                'total': 0,
                'time': datetime.now().strftime('%H:%M:%S')
            }
            
            # 分批获取数据（每批500只，并行请求）
            batch_size = 500
            batches = [all_codes[i:i+batch_size] for i in range(0, len(all_codes), batch_size)]
            
            # 使用线程池并行请求
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(cls._fetch_batch, batch) for batch in batches]
                
                for future in as_completed(futures):
                    batch_stats = future.result()
                    if batch_stats:
                        for key in stats:
                            if key != 'time':
                                stats[key] += batch_stats.get(key, 0)
            
            return stats
        except Exception as e:
            print(f"统计全市场失败: {e}")
            return None
    
    @classmethod
    def _fetch_batch(cls, codes: List[str]) -> Optional[Dict]:
        """获取一批股票数据并统计"""
        try:
            codes_str = ','.join(codes)
            url = f"{cls.TX_URL}{codes_str}"
            
            response = requests.get(url, timeout=15)
            response.encoding = 'gb2312'
            
            return cls._parse_and_count(response.text)
            
        except Exception as e:
            print(f"批量获取失败: {e}")
            return None
    
    @classmethod
    def _parse_and_count(cls, text: str) -> Dict:
        """解析腾讯接口数据并统计"""
        stats = {
            'up_count': 0,
            'down_count': 0,
            'flat_count': 0,
            'up_3pct': 0,
            'down_3pct': 0,
            'up_5pct': 0,
            'down_5pct': 0,
            'limit_up': 0,
            'limit_down': 0,
            'total': 0,
        }
        
        # 匹配每只股票的数据: v_sh600000="数据~数据~..."
        pattern = r'v_([^=]+)="([^"]*)"'
        matches = re.findall(pattern, text)
        
        for code, data in matches:
            if not data or data == "1" or 'pv_none_match' in code:
                continue
                
            fields = data.split('~')
            if len(fields) < 33:
                continue
            
            # 字段32是涨跌幅
            try:
                pct_str = fields[32]
                if not pct_str or pct_str == '':
                    continue
                pct = float(pct_str)
            except (ValueError, IndexError):
                continue
            
            stats['total'] += 1
            
            # 统计涨跌
            if pct > 0:
                stats['up_count'] += 1
            elif pct < 0:
                stats['down_count'] += 1
            else:
                stats['flat_count'] += 1
            
            # 统计幅度
            if pct >= 3:
                stats['up_3pct'] += 1
            elif pct <= -3:
                stats['down_3pct'] += 1
                
            if pct >= 5:
                stats['up_5pct'] += 1
            elif pct <= -5:
                stats['down_5pct'] += 1
            
            # 涨停跌停
            if pct >= 9.9:
                stats['limit_up'] += 1
            elif pct <= -9.9:
                stats['limit_down'] += 1
        
        return stats


if __name__ == "__main__":
    # 测试
    print("正在获取A股全市场数据（使用腾讯接口）...")
    stats = MarketStatsAPI.get_market_stats()
    if stats:
        print(f"\nA股统计 ({stats['time']}):")
        print(f"  总股票数: {stats['total']}")
        print(f"  上涨: {stats['up_count']} | 下跌: {stats['down_count']} | 平盘: {stats['flat_count']}")
        print(f"  涨>3%: {stats['up_3pct']} | 跌>3%: {stats['down_3pct']}")
        print(f"  涨>5%: {stats['up_5pct']} | 跌>5%: {stats['down_5pct']}")
        print(f"  涨停: {stats['limit_up']} | 跌停: {stats['limit_down']}")
