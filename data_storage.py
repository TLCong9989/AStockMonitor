# -*- coding: utf-8 -*-
"""
数据存储模块
使用Excel存储A股涨跌统计数据，支持按日期查询
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import os


class DataStorage:
    """Excel数据存储管理"""
    
    # 数据目录：使用用户文档目录/A股统计数据，确保打包后可读写
    DATA_DIR = Path.home() / "Documents" / "A股统计数据"
    
    # Excel文件名格式
    FILE_PREFIX = "market_stats"
    
    # 数据列定义
    COLUMNS = [
        'datetime',      # 采集时间
        'date',          # 日期
        'time',          # 时间
        'total',         # 总股票数
        'up_count',      # 上涨数
        'down_count',    # 下跌数
        'flat_count',    # 平盘数
        'up_3pct',       # 涨幅>3%
        'down_3pct',     # 跌幅>3%
        'up_5pct',       # 涨幅>5%
        'down_5pct',     # 跌幅>5%
        'limit_up',      # 涨停
        'limit_down',    # 跌停
    ]
    
    def __init__(self):
        """初始化，确保数据目录存在"""
        self.DATA_DIR.mkdir(exist_ok=True)
        
    def get_file_path(self, date: datetime = None) -> Path:
        """获取指定日期的Excel文件路径"""
        if date is None:
            date = datetime.now()
        filename = f"{self.FILE_PREFIX}_{date.strftime('%Y-%m')}.xlsx"
        return self.DATA_DIR / filename
    
    def save_stats(self, stats: Dict) -> bool:
        """
        保存一条统计数据
        
        Args:
            stats: 包含涨跌统计的字典
        
        Returns:
            是否保存成功
        """
        try:
            now = datetime.now()
            file_path = self.get_file_path(now)
            
            # 构建新数据行
            new_row = {
                'datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'total': stats.get('total', 0),
                'up_count': stats.get('up_count', 0),
                'down_count': stats.get('down_count', 0),
                'flat_count': stats.get('flat_count', 0),
                'up_3pct': stats.get('up_3pct', 0),
                'down_3pct': stats.get('down_3pct', 0),
                'up_5pct': stats.get('up_5pct', 0),
                'down_5pct': stats.get('down_5pct', 0),
                'limit_up': stats.get('limit_up', 0),
                'limit_down': stats.get('limit_down', 0),
            }
            
            # 读取或创建DataFrame
            if file_path.exists():
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                df = pd.DataFrame(columns=self.COLUMNS)
            
            # 添加新行
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
            # 保存
            df.to_excel(file_path, index=False, engine='openpyxl')
            return True
            
        except Exception as e:
            print(f"保存数据失败: {e}")
            return False
    
    def get_today_data(self) -> Optional[pd.DataFrame]:
        """获取今天的数据"""
        today = datetime.now().strftime('%Y-%m-%d')
        return self._query_by_date_range(today, today)
    
    def get_week_data(self) -> Optional[pd.DataFrame]:
        """获取本周的数据（周一到今天）"""
        today = datetime.now()
        # 计算本周一
        monday = today - timedelta(days=today.weekday())
        start_date = monday.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        return self._query_by_date_range(start_date, end_date)
    
    def get_month_data(self) -> Optional[pd.DataFrame]:
        """获取本月的数据"""
        today = datetime.now()
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        return self._query_by_date_range(start_date, end_date)
    
    def get_date_range_data(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取指定日期范围的数据"""
        return self._query_by_date_range(start_date, end_date)
    
    def _query_by_date_range(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        按日期范围查询数据
        
        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
        """
        try:
            # 解析日期
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 可能跨月，需要读取多个文件
            all_data = []
            current = start.replace(day=1)
            
            while current <= end:
                file_path = self.get_file_path(current)
                if file_path.exists():
                    df = pd.read_excel(file_path, engine='openpyxl')
                    all_data.append(df)
                
                # 移动到下个月
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            
            if not all_data:
                return pd.DataFrame(columns=self.COLUMNS)
            
            # 合并数据
            df = pd.concat(all_data, ignore_index=True)
            
            # 过滤日期范围
            df['date'] = pd.to_datetime(df['date'])
            mask = (df['date'] >= start_date) & (df['date'] <= end_date)
            result = df[mask].copy()
            result['date'] = result['date'].dt.strftime('%Y-%m-%d')
            
            return result.sort_values('datetime').reset_index(drop=True)
            
        except Exception as e:
            print(f"查询数据失败: {e}")
            return None
    
    def get_single_day_data(self, date: str) -> Optional[pd.DataFrame]:
        """获取某一天的数据"""
        return self._query_by_date_range(date, date)
    
    def get_latest_record(self) -> Optional[Dict]:
        """获取最新一条记录"""
        df = self.get_today_data()
        if df is not None and len(df) > 0:
            return df.iloc[-1].to_dict()
        return None
    
    def get_stats_summary(self, df: pd.DataFrame) -> Dict:
        """
        获取数据统计摘要
        
        Returns:
            包含平均值、最大值、最小值等统计信息
        """
        if df is None or len(df) == 0:
            return {}
        
        numeric_cols = ['up_count', 'down_count', 'up_3pct', 'down_3pct', 
                       'up_5pct', 'down_5pct', 'limit_up', 'limit_down']
        
        summary = {
            'record_count': len(df),
            'date_range': f"{df['date'].min()} ~ {df['date'].max()}",
        }
        
        for col in numeric_cols:
            if col in df.columns:
                summary[f'{col}_avg'] = round(df[col].mean(), 1)
                summary[f'{col}_max'] = int(df[col].max())
                summary[f'{col}_min'] = int(df[col].min())
        
        return summary
    
    def list_data_files(self) -> List[str]:
        """列出所有数据文件"""
        files = list(self.DATA_DIR.glob(f"{self.FILE_PREFIX}_*.xlsx"))
        return sorted([f.name for f in files])


if __name__ == "__main__":
    # 测试
    storage = DataStorage()
    
    # 模拟保存数据
    test_stats = {
        'total': 5757,
        'up_count': 1509,
        'down_count': 3493,
        'flat_count': 755,
        'up_3pct': 258,
        'down_3pct': 310,
        'up_5pct': 116,
        'down_5pct': 52,
        'limit_up': 53,
        'limit_down': 7,
    }
    
    print("保存测试数据...")
    storage.save_stats(test_stats)
    
    print("\n今日数据:")
    df = storage.get_today_data()
    if df is not None:
        print(df)
    
    print("\n数据文件列表:")
    print(storage.list_data_files())

