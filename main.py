# -*- coding: utf-8 -*-
"""
A股实时涨跌统计面板
- 实时采集全A股涨跌数据
- 自动保存到Excel
- 支持查询当天/本周/本月历史数据
- 支持深色/浅色主题切换
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib
import threading
import time
from collections import deque
import pandas as pd
import platform

# 中文字体
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
matplotlib.rcParams['axes.unicode_minus'] = False

from market_api import MarketStatsAPI
from data_storage import DataStorage


class MarketStatsPanel:
    """A股实时涨跌统计面板"""
    
    # 主题配置
    THEMES = {
        'dark': {
            'bg': '#1a1a2e',
            'fg': '#00d4ff',
            'text': '#cccccc',
            'chart_bg': '#252540',
            'chart_line': '#444444',
            'chart_text': '#888888',
            'status_bg': '#151525',
            'btn_start': '#aa0000',
            'btn_stop': '#00aa55',
            'btn_normal': '#4a4a6a',
            'btn_text': '#ffffff'
        },
        'light': {
            'bg': '#f0f2f5',
            'fg': '#1890ff',
            'text': '#333333',
            'chart_bg': '#ffffff',
            'chart_line': '#e8e8e8',
            'chart_text': '#666666',
            'status_bg': '#e6e6e6',
            'btn_start': '#ff4d4f',
            'btn_stop': '#52c41a',
            'btn_normal': '#1890ff',
            'btn_text': '#ffffff'
        }
    }
    
    # 颜色配置：红涨绿跌（固定）
    COLOR_UP = '#ff4444'
    COLOR_DOWN = '#00cc00'
    
    def __init__(self, root):
        self.root = root
        self.root.title("📊 A股实时涨跌统计")
        self.root.geometry("1300x850")
        
        # 检查是否为 macOS
        self.is_macos = platform.system() == 'Darwin'
        
        # 初始化状态
        self.current_theme = 'dark'
        self.theme = self.THEMES[self.current_theme]
        self.root.configure(bg=self.theme['bg'])
        
        # 数据存储
        self.storage = DataStorage()
        
        # 实时数据（内存中保留最近100个点用于显示）
        self.max_points = 100
        self.time_labels = deque(maxlen=self.max_points)
        self.data = {
            'up_count': deque(maxlen=self.max_points),
            'down_count': deque(maxlen=self.max_points),
            'up_3pct': deque(maxlen=self.max_points),
            'down_3pct': deque(maxlen=self.max_points),
            'up_5pct': deque(maxlen=self.max_points),
            'down_5pct': deque(maxlen=self.max_points),
            'limit_up': deque(maxlen=self.max_points),
            'limit_down': deque(maxlen=self.max_points),
        }
        
        self.is_running = False
        self.update_interval = 10
        self.current_view = 'realtime'
        
        self.setup_ui()
        self.load_today_data()
        self.apply_theme()
        
    def setup_ui(self):
        """设置界面"""
        # 顶部控制栏
        self.header = tk.Frame(self.root, height=70)
        self.header.pack(fill=tk.X, padx=20, pady=10)
        self.header.pack_propagate(False)
        
        # 左侧：标题
        left_frame = tk.Frame(self.header)
        left_frame.pack(side=tk.LEFT)
        
        self.title_label = tk.Label(left_frame, text="📊 A股实时涨跌统计", font=('Arial', 18, 'bold'))
        self.title_label.pack(side=tk.LEFT)
        
        # 中间：数据视图切换
        self.view_frame = tk.Frame(self.header)
        self.view_frame.pack(side=tk.LEFT, padx=50)
        
        self.view_label = tk.Label(self.view_frame, text="数据视图:", font=('Arial', 11))
        self.view_label.pack(side=tk.LEFT, padx=5)
        
        self.view_var = tk.StringVar(value="realtime")
        views = [("实时", "realtime"), ("今日", "today"), 
                ("本周", "week"), ("本月", "month")]
        
        self.view_radios = []
        for text, value in views:
            rb = tk.Radiobutton(self.view_frame, text=text, variable=self.view_var,
                               value=value, command=self.on_view_change,
                               font=('Arial', 11), indicatoron=0, width=6,
                               selectcolor='', relief=tk.FLAT)
            rb.pack(side=tk.LEFT, padx=2)
            self.view_radios.append(rb)
        
        # 右侧：控制按钮
        right_frame = tk.Frame(self.header)
        right_frame.pack(side=tk.RIGHT)
        
        # 采集间隔
        self.interval_label = tk.Label(right_frame, text="采集间隔:", font=('Arial', 10))
        self.interval_label.pack(side=tk.LEFT, padx=5)
        
        self.interval_var = tk.StringVar(value="10")
        self.interval_combo = ttk.Combobox(right_frame, textvariable=self.interval_var,
                                      values=["5", "10", "15", "30", "60"],
                                      width=4, state='readonly')
        self.interval_combo.pack(side=tk.LEFT, padx=3)
        self.interval_combo.bind('<<ComboboxSelected>>', self.on_interval_change)
        
        self.sec_label = tk.Label(right_frame, text="秒", font=('Arial', 10))
        self.sec_label.pack(side=tk.LEFT)
        
        # 主题切换按钮
        self.theme_btn = tk.Button(right_frame, text="🌗", 
                                  command=self.toggle_theme,
                                  font=('Arial', 12), width=3, relief=tk.FLAT)
        self.theme_btn.pack(side=tk.LEFT, padx=10)
        
        # 开始/停止
        self.start_btn = tk.Button(right_frame, text="▶ 开始采集", 
                                   command=self.toggle_monitor,
                                   font=('Arial', 11, 'bold'),
                                   width=12, relief=tk.FLAT)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        # 刷新历史
        self.refresh_btn = tk.Button(right_frame, text="🔄 刷新", 
                               command=self.refresh_current_view,
                               font=('Arial', 10), width=6, relief=tk.FLAT)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # 打开数据目录
        self.folder_btn = tk.Button(right_frame, text="📁 数据", 
                              command=self.open_data_folder,
                              font=('Arial', 10), width=6, relief=tk.FLAT)
        self.folder_btn.pack(side=tk.LEFT, padx=5)
        
        # 图表区域
        self.chart_frame = tk.Frame(self.root)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.setup_charts()
        
        # 状态栏
        self.status_frame = tk.Frame(self.root, height=40)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_frame.pack_propagate(False)
        
        self.status_var = tk.StringVar(value="就绪 | 点击「开始采集」获取数据")
        self.status_label = tk.Label(self.status_frame, textvariable=self.status_var,
                                    font=('Arial', 10))
        self.status_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.stats_var = tk.StringVar(value="")
        self.stats_label = tk.Label(self.status_frame, textvariable=self.stats_var,
                                   font=('Arial', 10))
        self.stats_label.pack(side=tk.RIGHT, padx=15, pady=10)
        
    def setup_charts(self):
        """设置图表"""
        self.fig = Figure(figsize=(13, 8))
        self.fig.subplots_adjust(hspace=0.35, wspace=0.2, 
                                  left=0.06, right=0.96, top=0.92, bottom=0.08)
        
        self.axes = []
        self.titles = ['上涨/下跌 家数', '涨幅>5% / 跌幅>5%',
                       '涨幅>3% / 跌幅>3%', '涨停 / 跌停']
        
        for i in range(4):
            ax = self.fig.add_subplot(2, 2, i + 1)
            self.axes.append(ax)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def apply_btn_style(self, btn, bg_color, text_color):
        """适配 macOS 的按钮样式"""
        if self.is_macos:
            # macOS 下 bg 属性可能失效，使用 highlightbackground
            try:
                btn.configure(highlightbackground=bg_color, fg=text_color)
            except:
                pass
        else:
            btn.configure(bg=bg_color, fg=text_color)

    def apply_theme(self):
        """应用当前主题"""
        t = self.theme
        
        # 窗口背景
        self.root.configure(bg=t['bg'])
        self.header.configure(bg=t['bg'])
        self.chart_frame.configure(bg=t['bg'])
        
        # 标题及文字
        self.title_label.configure(bg=t['bg'], fg=t['fg'])
        
        # 视图切换区
        self.view_frame.configure(bg=t['bg'])
        self.view_label.configure(bg=t['bg'], fg=t['text'])
        for rb in self.view_radios:
            rb.configure(bg=t['bg'], fg=t['text'], 
                        activebackground=t['bg'], selectcolor=t['chart_bg'])
        
        # 右侧控制区
        for w in [self.header.winfo_children()[-1], self.interval_label, self.sec_label]:
            if isinstance(w, tk.Frame):
                w.configure(bg=t['bg'])
            elif isinstance(w, tk.Label):
                w.configure(bg=t['bg'], fg=t['text'])
        
        # 按钮样式 (使用辅助函数)
        self.apply_btn_style(self.theme_btn, t['btn_normal'], t['btn_text'])
        self.apply_btn_style(self.refresh_btn, t['btn_normal'], t['btn_text'])
        self.apply_btn_style(self.folder_btn, t['btn_normal'], t['btn_text'])
        
        if self.is_running:
            self.apply_btn_style(self.start_btn, t['btn_stop'], t['btn_text'])
        else:
            self.apply_btn_style(self.start_btn, t['btn_start'], t['btn_text'])
            
        # 状态栏
        self.status_frame.configure(bg=t['status_bg'])
        self.status_label.configure(bg=t['status_bg'], fg=t['chart_text'])
        self.stats_label.configure(bg=t['status_bg'], fg=t['fg'])
        
        # 图表样式
        self.fig.patch.set_facecolor(t['bg'])
        for ax, title in zip(self.axes, self.titles):
            ax.set_facecolor(t['chart_bg'])
            ax.set_title(title, color=t['fg'], fontsize=12, fontweight='bold')
            ax.tick_params(colors=t['chart_text'], labelsize=9)
            for spine in ax.spines.values():
                spine.set_color(t['chart_line'])
            ax.grid(True, linestyle='--', alpha=0.3, color=t['chart_line'])
            
            # 更新图例文字颜色
            legend = ax.get_legend()
            if legend:
                plt.setp(legend.get_texts(), color=t['text'])
                legend.get_frame().set_facecolor(t['chart_bg'])
                legend.get_frame().set_edgecolor(t['chart_line'])
        
        self.canvas.draw()
        
    def toggle_theme(self):
        """切换深色/浅色主题"""
        self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        self.theme = self.THEMES[self.current_theme]
        self.apply_theme()
        
    def toggle_monitor(self):
        """开始/停止监控"""
        if self.is_running:
            # 停止
            self.is_running = False
            self.start_btn.config(text="▶ 开始采集")
            self.apply_btn_style(self.start_btn, self.theme['btn_start'], self.theme['btn_text'])
            self.status_var.set("已停止采集")
            
            self.interval_combo.config(state='readonly')
            for rb in self.view_radios:
                rb.config(state='normal')
        else:
            # 开始
            self.is_running = True
            self.start_btn.config(text="⏹ 停止采集")
            self.apply_btn_style(self.start_btn, self.theme['btn_stop'], self.theme['btn_text'])
            self.status_var.set("正在初始化采集...")
            
            self.interval_combo.config(state='disabled')
            self.view_var.set('realtime')
            self.current_view = 'realtime'
            
            threading.Thread(target=self.monitor_loop, daemon=True).start()
            
    def monitor_loop(self):
        """监控循环"""
        while self.is_running:
            start_time = time.time()
            
            # 执行采集
            self.root.after(0, lambda: self.status_var.set("正在获取数据..."))
            self.fetch_and_save()
            
            # 计算等待时间
            elapsed = time.time() - start_time
            wait_time = max(1, self.update_interval - elapsed)
            
            # 等待
            time.sleep(wait_time)
            
    def fetch_and_save(self):
        """获取数据、保存并更新图表"""
        try:
            stats = MarketStatsAPI.get_market_stats()
            if stats:
                # 保存
                self.storage.save_stats(stats)
                
                # 更新内存
                self.time_labels.append(datetime.now().strftime('%H:%M'))
                for k in self.data:
                    if k in stats:
                        self.data[k].append(stats[k])
                
                # UI更新
                if self.current_view == 'realtime':
                    self.root.after(0, lambda s=stats: self.update_ui_realtime(s))
            else:
                 self.root.after(0, lambda: self.status_var.set("采集失败: 接口无响应"))
                    
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"采集出错: {e}"))
            
    def update_ui_realtime(self, stats):
        """更新实时界面"""
        self.update_charts_from_memory()
        self.status_var.set(f"正在采集... | 数据点: {len(self.time_labels)} | "
                           f"更新: {stats['time']}")
        self.stats_var.set(f"上涨: {stats['up_count']} | 下跌: {stats['down_count']} | "
                          f"涨停: {stats['limit_up']} | 跌停: {stats['limit_down']}")
        
    def _draw_charts(self, x_labels, data_provider):
        """通用绘图方法
        Args:
            x_labels: X轴标签列表
            data_provider: 数据提供函数，接收(key)返回数据列表
        """
        if not x_labels:
            return
            
        x = list(range(len(x_labels)))
        t = self.theme
        
        chart_config = [
            (0, 'up_count', 'down_count', '上涨', '下跌', '上涨/下跌 家数'),
            (1, 'up_5pct', 'down_5pct', '涨>5%', '跌>5%', '涨幅>5% / 跌幅>5%'),
            (2, 'up_3pct', 'down_3pct', '涨>3%', '跌>3%', '涨幅>3% / 跌幅>3%'),
            (3, 'limit_up', 'limit_down', '涨停', '跌停', '涨停 / 跌停'),
        ]
        
        for ax_idx, up_key, down_key, up_label, down_label, title in chart_config:
            ax = self.axes[ax_idx]
            ax.clear()
            
            # 重绘样式
            ax.set_facecolor(t['chart_bg'])
            ax.set_title(title, color=t['fg'], fontsize=12, fontweight='bold')
            ax.tick_params(colors=t['chart_text'], labelsize=9)
            for spine in ax.spines.values():
                spine.set_color(t['chart_line'])
            ax.grid(True, linestyle='--', alpha=0.3, color=t['chart_line'])
            
            # 获取数据
            up_data = list(data_provider(up_key))
            down_data = list(data_provider(down_key))
            
            if up_data and len(up_data) == len(x):
                ax.plot(x, up_data, color=self.COLOR_UP, linewidth=2,
                       label=f'{up_label}: {up_data[-1]}', marker='o', markersize=3)
                ax.plot(x, down_data, color=self.COLOR_DOWN, linewidth=2,
                       label=f'{down_label}: {down_data[-1]}', marker='o', markersize=3)
                
            # X轴标签
            if x:
                step = max(1, len(x) // 10)
                ax.set_xticks(x[::step])
                ax.set_xticklabels(list(x_labels)[::step], 
                                 rotation=45, ha='right', fontsize=8)
            
            ax.legend(loc='upper left', fontsize=9,
                     facecolor=t['chart_bg'], edgecolor=t['chart_line'],
                     labelcolor=t['text'])
        
        self.canvas.draw()

    def update_charts_from_memory(self):
        """刷新实时图表"""
        if not self.time_labels:
            return
        self._draw_charts(self.time_labels, lambda k: self.data[k])

    def load_today_data(self):
        """加载今日数据"""
        df = self.storage.get_today_data()
        if df is not None and len(df) > 0:
            self.time_labels.clear()
            for k in self.data: self.data[k].clear()
            
            for _, row in df.iterrows():
                self.time_labels.append(row['time'][:5])
                for k in self.data:
                    if k in row:
                        self.data[k].append(row[k])
            self.update_charts_from_memory()
            
    def on_view_change(self):
        self.current_view = self.view_var.get()
        self.refresh_current_view()
        
    def on_interval_change(self, event):
        self.update_interval = int(self.interval_var.get())
        self.status_var.set(f"采集间隔已设置为 {self.update_interval} 秒")
        
    def open_data_folder(self):
        import subprocess
        subprocess.run(['open', str(self.storage.DATA_DIR)])
        
    def refresh_current_view(self):
        if self.current_view == 'realtime':
            self.update_charts_from_memory()
        elif self.current_view == 'today':
            self.load_and_display(self.storage.get_today_data(), "今日")
        elif self.current_view == 'week':
            self.load_and_display(self.storage.get_week_data(), "本周")
        elif self.current_view == 'month':
            self.load_and_display(self.storage.get_month_data(), "本月")
            
    def load_and_display(self, df, label):
        """显示历史数据"""
        if df is None or len(df) == 0:
            self.status_var.set(f"{label}暂无数据")
            for ax in self.axes: ax.clear()
            self.canvas.draw()
            return
            
        # 准备X轴标签：如果有日期变化则显示日期+时间，否则只显示时间
        dates = df['date'].astype(str).unique()
        if len(dates) > 1:
            # 跨天显示：MM-DD HH:MM
            x_labels = (df['date'].astype(str).str[5:] + ' ' + df['time'].str[:5]).tolist()
        else:
            # 单天显示：HH:MM
            x_labels = df['time'].str[:5].tolist()
            
        # 绘图
        self._draw_charts(x_labels, lambda k: df[k].tolist())
        
        # 更新状态栏摘要
        summary = self.storage.get_stats_summary(df)
        self.status_var.set(f"{label}数据 | 共 {len(df)} 条记录 | {summary.get('date_range', '')}")
        self.stats_var.set(f"上涨均值: {summary.get('up_count_avg', 0)} | "
                          f"下跌均值: {summary.get('down_count_avg', 0)}") 


def main():
    root = tk.Tk()
    app = MarketStatsPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
