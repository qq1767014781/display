# main.py
import queue
import signal
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import subprocess
import os
from xml.dom import minidom
from xml.sax import parseString

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
import xml.etree.ElementTree as ET
from tkinter import ttk
import sqlite3
from tkinter import simpledialog

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

class FurnacePlanningModule(tk.Frame):
    """组炉组浇模块"""
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(bg="#E8F5E9")
        self.process = None
        self.create_widgets()
        self.load_settings()
        self.load_input_data()
        self.load_cast_results()

    def create_widgets(self):
        """创建三大子模块"""
        # 参数配置模块
        param_frame = ttk.LabelFrame(self, text="参数配置")
        param_frame.pack(fill="x", padx=10, pady=5)
        self.create_param_controls(param_frame)

        # 输入数据展示模块
        input_frame = ttk.LabelFrame(self, text="输入数据展示")
        input_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.create_input_display(input_frame)

        # 结果展示模块
        result_frame = ttk.LabelFrame(self, text="浇注计划结果")
        result_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.create_result_table(result_frame)

    # ----------------- 参数配置模块 -----------------
    def create_param_controls(self, parent):
        """创建参数输入控件"""
        self.param_entries = {}
        params = [("timeLimit", "时间限制"), ("smDiv", "SM分区")]
        for i, (param, label) in enumerate(params):
            row = ttk.Frame(parent)
            row.pack(fill="x", padx=5, pady=2)

            ttk.Label(row, text=label + ":", width=12).pack(side="left")
            entry = ttk.Entry(row, width=15)
            entry.pack(side="left", padx=5)
            self.param_entries[param] = entry

        # 按钮组
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="保存配置", command=self.save_settings).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="运行程序", command=self.run_furnace_plan).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="中止运行", command=self.stop_furnace_plan).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="导出到数据库", command=self.export_cast_plan).pack(side="left", padx=5)

    def export_cast_plan(self):
        """为每个 Heat 生成唯一 heat_id，格式：chargeNo_minLength_序号"""
        try:
            dom = minidom.parse("castInput.xml")
            conn = sqlite3.connect('steel_production.db')
            cursor = conn.cursor()

            # 创建表（保持原结构）
            cursor.execute('''CREATE TABLE IF NOT EXISTS production (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            heat_id TEXT UNIQUE,  -- 添加唯一约束
                            order_no TEXT,
                            furnace_no TEXT,
                            width INTEGER,
                            status TEXT)''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS cast_plan (
                            heat_id TEXT,
                            cast_no TEXT,
                            charge_no TEXT,
                            order_no TEXT,
                            min_length INTEGER,
                            max_length INTEGER,
                            PRIMARY KEY (heat_id, cast_no))''')

            with conn:
                cursor.execute("DELETE FROM production")
                cursor.execute("DELETE FROM cast_plan")

                # 遍历 XML 结构
                heat_counter = 1  # 每个 Charge 节点重置计数器
                for cast in dom.getElementsByTagName("Cast"):
                    cast_no = cast.getAttribute("chargeNum")
                    if not cast_no:
                        raise ValueError("Cast 节点缺少 chargeNum 属性")

                    for charge in cast.getElementsByTagName("Charge"):
                        charge_lgst = charge.getAttribute("lgSt")


                        for heat in charge.getElementsByTagName("Heat"):
                            # 提取字段
                            charge_no = heat.getAttribute("chargeNo")
                            order_no = heat.getAttribute("orderNo")
                            min_length = heat.getAttribute("minLength")
                            max_length = heat.getAttribute("maxLength")

                            # 校验必要字段
                            if not charge_no:
                                raise ValueError("Heat 节点缺少 chargeNo 属性")
                            if not min_length.isdigit() or not max_length.isdigit():
                                raise ValueError(f"minLength/maxLength 必须是数字 (Heat: {charge_no})")

                            # 生成唯一 heat_id（chargeNo_minLength_序号）
                            heat_id = f"{charge_no}_{min_length}_{heat_counter}"
                            heat_counter += 1  # 递增计数器

                            # 插入 production 表
                            cursor.execute('''INSERT INTO production 
                                           (heat_id, order_no, furnace_no, width, status)
                                           VALUES (?, ?, ?, ?, ?)''',
                                           (heat_id, order_no, charge_no, int(min_length), "1"))

                            # 插入 cast_plan 表
                            cursor.execute('''INSERT INTO cast_plan 
                                           (heat_id, cast_no, charge_no, order_no, min_length, max_length)
                                           VALUES (?, ?, ?, ?, ?, ?)''',
                                           (heat_id, cast_no, charge_lgst, order_no,
                                            int(min_length), int(max_length)))

                # 统计结果
                prod_count = cursor.execute("SELECT COUNT(*) FROM production").fetchone()[0]
                cast_count = cursor.execute("SELECT COUNT(*) FROM cast_plan").fetchone()[0]
                messagebox.showinfo("成功", f"导出完成\n生产表：{prod_count}条\n浇次计划表：{cast_count}条")

        except Exception as e:
            messagebox.showerror("失败", f"导出失败: {str(e)}")

        except Exception as e:
            messagebox.showerror("失败", f"导出失败: {str(e)}")
    def save_settings(self):
        """保存参数到JSON文件"""
        settings = {
            "timeLimit": self.param_entries["timeLimit"].get(),
            "smDiv": self.param_entries["smDiv"].get()
        }
        try:
            with open("furnaceSetting.json", "w") as f:
                json.dump(settings, f, indent=4)
            messagebox.showinfo("成功", "参数保存成功")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def load_settings(self):
        """加载参数配置"""
        try:
            with open("furnaceSetting.json") as f:
                settings = json.load(f)
                for param, entry in self.param_entries.items():
                    entry.delete(0, tk.END)
                    entry.insert(0, settings.get(param, ""))
        except FileNotFoundError:
            pass

    # ----------------- 程序控制 -----------------
    def run_furnace_plan(self):
        """运行组炉程序"""
        if self.process and self.process.poll() is None:
            messagebox.showwarning("警告", "程序已在运行中")
            return

        try:
            self.process = subprocess.Popen("furnacePlan.exe", shell=True)
        except Exception as e:
            messagebox.showerror("错误", f"程序启动失败: {str(e)}")

    def stop_furnace_plan(self):
        """中止程序运行"""
        if self.process is None or self.process.poll() is not None:
            messagebox.showinfo("提示", "没有正在运行的程序")
            return

        try:
            if os.name == 'nt':
                subprocess.run(f"taskkill /F /T /PID {self.process.pid}", shell=True)
            else:
                os.kill(self.process.pid, signal.SIGTERM)
            messagebox.showinfo("成功", "程序已中止")
            self.process = None
        except Exception as e:
            messagebox.showerror("错误", f"中止失败: {str(e)}")

    # ----------------- 输入数据展示模块 -----------------
    def create_input_display(self, parent):
        """创建表格形式的XML数据展示"""
        # 创建带滚动条的Treeview
        self.input_tree = ttk.Treeview(parent, columns=(
            "furnace_no", "slab_num", "weight",
            "cc_list", "width_max", "width_min"
        ), show="headings")

        # 配置滚动条
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.input_tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.input_tree.xview)
        self.input_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 配置列定义
        columns = {
            "furnace_no": ("炉号", 150),
            "slab_num": ("板坯数", 80),
            "weight": ("重量（吨）", 100),
            "cc_list": ("可用机器列表", 120),
            "width_max": ("最大宽度（mm）", 120),
            "width_min": ("最小宽度（mm）", 120)
        }

        # 设置列标题
        for col, (text, width) in columns.items():
            self.input_tree.heading(col, text=text)
            self.input_tree.column(col, width=width, anchor="center")

        # 设置交替行颜色
        self.input_tree.tag_configure("oddrow", background="#F0F8FF")
        self.input_tree.tag_configure("evenrow", background="#E0FFFF")

        # 布局
        self.input_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # 设置网格行列权重
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

    def load_input_data(self):
        """加载并展示FurnaceResult数据"""
        try:
            # 清空现有数据
            for item in self.input_tree.get_children():
                self.input_tree.delete(item)

            tree = ET.parse("FurnaceResult2.xml")

            # 遍历每个FurnaceResult
            for idx, result in enumerate(tree.findall(".//FurnaceResult")):
                # 提取数据
                values = (
                    self._get_text(result, "FURNACE_NO"),
                    self._get_text(result, "SLAB_NUM"),
                    self._get_text(result, "FURNACE_WT"),
                    self._get_text(result, "FURNACE_AVAILABLE_CC_LIST"),
                    self._get_text(result, "FURNACE_WIDTH_MAX"),
                    self._get_text(result, "FURNACE_WIDTH_MIN")
                )

                # 插入表格并设置交替颜色
                tag = "evenrow" if idx % 2 == 0 else "oddrow"
                self.input_tree.insert("", "end", values=values, tags=(tag,))

        except Exception as e:
            messagebox.showerror("错误", f"加载XML数据失败: {str(e)}")

    def _get_text(self, element, tag):
        """安全获取XML节点文本"""
        node = element.find(tag)
        return node.text if node is not None else "N/A"

    # ----------------- 结果展示模块 -----------------
    def create_result_table(self, parent):
        """创建可展开的浇注计划表格"""
        self.cast_tree = ttk.Treeview(parent, columns=("value",), show="tree")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.cast_tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.cast_tree.xview)

        self.cast_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 配置样式
        self.cast_tree.tag_configure("cast", background="#B0E0E6")
        self.cast_tree.tag_configure("charge", background="#98FB98")
        self.cast_tree.tag_configure("heat", background="white")

        self.cast_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

    def load_cast_results(self):
        """加载浇注计划结果"""
        try:
            tree = ET.parse("castInput.xml")
            root = tree.getroot()

            # 清空现有数据
            for item in self.cast_tree.get_children():
                self.cast_tree.delete(item)

            # 添加层次数据
            for cast in root.findall("Cast"):
                cast_id = self.cast_tree.insert("", "end",
                                                text=f"浇次 (炉数: {cast.attrib['chargeNum']})",
                                                tags=("cast",))

                for charge in cast.findall("Charge"):
                    charge_id = self.cast_tree.insert(cast_id, "end",
                                                      text=f"炉次 (实际长度: {charge.attrib['realLength']}mm)",
                                                      tags=("charge",))

                    for heat in charge.findall("Heat"):
                        self.cast_tree.insert(charge_id, "end",
                                              text=f"钢水 | 订单号: {heat.attrib['orderNo']} "
                                                   f"长度范围: {heat.attrib['minLength']}-{heat.attrib['maxLength']}mm",
                                              tags=("heat",))
        except Exception as e:
            messagebox.showerror("错误", f"加载浇注计划失败: {str(e)}")

class SteelCastingModule(tk.Frame):
    """炼钢连铸模块"""

    def __init__(self, parent):
        super().__init__(parent)
        # 新增日志窗口控制参数
        self.log_window = None
        self.process = None
        self.log_queue = queue.Queue()
        self.log_thread = None

        self.configure(background="#E8F5E9")
        self.process = None
        self.highlight_items = set()

        # ========== 新增初始化参数 ==========
        # Y轴滚动控制
        self.current_ypos = 0  # 当前垂直滚动位置（设备起始索引）
        self.visible_machines = 10  # 默认可见设备数量
        self.total_machines = 0  # 总设备数（数据加载后更新）

        # X轴滚动控制
        self.current_x_start = 0  # 当前水平滚动位置（时间起始点）
        self.view_width = 20000  # 固定视图宽度

        # ========== 初始化控件 ==========
        self.create_widgets()
        self.load_settings()
        self.load_result()
        self.process = None

    def create_log_window(self):
        """创建日志窗口"""
        self.log_window = tk.Toplevel(self)
        self.log_window.title("程序执行日志")

        # 日志文本框
        self.log_text = tk.Text(self.log_window, wrap=tk.WORD, height=20, width=80)
        scrollbar = ttk.Scrollbar(self.log_window, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # 控制按钮
        self.stop_btn = ttk.Button(self.log_window, text="中止执行", command=self.stop_program)

        # 布局
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.stop_btn.grid(row=1, column=0, columnspan=2, pady=5)

        self.log_window.grid_rowconfigure(0, weight=1)
        self.log_window.grid_columnconfigure(0, weight=1)

        # 开始更新日志
        self.update_log()

    def update_log(self):
        """定时更新日志显示"""
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_text.insert(tk.END, msg)
            self.log_text.see(tk.END)
        self.log_window.after(100, self.update_log)

    def create_widgets(self):
        """创建三个子模块"""
        # 参数配置模块
        param_frame = ttk.LabelFrame(self, text="参数配置与程序启动")
        param_frame.pack(fill="x", padx=10, pady=5)
        self.create_param_controls(param_frame)

        # 甘特图模块
        self.gantt_frame = ttk.LabelFrame(self, text="生产计划甘特图")
        self.gantt_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.create_gantt_chart()

        # 数据表格模块
        table_frame = ttk.LabelFrame(self, text="生产数据明细")
        table_frame.pack(fill="both", padx=10, pady=5)
        self.create_data_table(table_frame)

    def create_param_controls(self, parent):
        """参数输入控件"""
        params = ["Start", "End", "Diff", "time_limit"]
        self.entries = {}

        for i, param in enumerate(params):
            row = ttk.Frame(parent)
            row.pack(fill="x", padx=5, pady=2)

            ttk.Label(row, text=param + ":", width=12).pack(side="left")
            entry = ttk.Entry(row, width=10)
            entry.pack(side="left", padx=5)
            self.entries[param] = entry

        # 按钮组
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="保存配置", command=self.save_settings).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="执行程序", command=self.run_program).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="中止执行", command=self.stop_program).pack(side="left", padx=5)

    def create_gantt_chart(self):
        """创建甘特图画布和滚动条"""
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)

        # 创建画布
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.gantt_frame)
        self.canvas_widget = self.canvas.get_tk_widget()

        # 创建滚动条（仅绑定命令，不配置其他参数）
        self.gantt_vscroll = ttk.Scrollbar(self.gantt_frame, orient="vertical", command=self.on_y_scroll)
        self.gantt_hscroll = ttk.Scrollbar(self.gantt_frame, orient="horizontal", command=self.on_x_scroll)

        # 布局
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")
        self.gantt_vscroll.grid(row=0, column=1, sticky="ns")
        self.gantt_hscroll.grid(row=1, column=0, sticky="ew")

        # 配置权重
        self.gantt_frame.grid_rowconfigure(0, weight=1)
        self.gantt_frame.grid_columnconfigure(0, weight=1)

    def on_y_scroll(self, *args):
        """处理垂直滚动事件（仅响应滚动条操作）"""
        if self.total_machines <= self.visible_machines:
            return

        event_type = args[0]
        max_scroll = self.total_machines - self.visible_machines

        # 计算新位置
        if event_type == "moveto":
            fraction = float(args[1])
            new_ypos = int(fraction * max_scroll)
        elif event_type == "scroll":
            step = int(args[1])
            new_ypos = self.current_ypos + step  # ✅ 使用已初始化的属性
        else:
            return

        # 更新位置
        new_ypos = max(0, min(new_ypos, max_scroll))
        if new_ypos != self.current_ypos:
            self.current_ypos = new_ypos
            self.update_gantt()

    def on_gantt_scroll(self, *args):
        """处理滚动事件"""
        if not self.result_data or self.xmax_total <= self.view_width:
            return  # 无数据或无需滚动时直接返回

        # 解析滚动类型
        event_type = args[0]

        # 计算可滚动范围
        max_scroll = self.xmax_total - self.view_width

        # 获取当前视图起始位置
        current_start = self.ax.get_xlim()[0]

        # 解析滚动动作
        if event_type == "moveto":
            # 拖动滑块
            fraction = float(args[1])
            new_start = fraction * max_scroll
        elif event_type == "scroll":
            # 点击箭头步进滚动（每次滚动200单位）
            step = int(args[1])
            current_start = self.ax.get_xlim()[0]
            new_start = current_start + step * 200
        else:
            return

        # 限制滚动范围
        new_start = max(0, min(new_start, max_scroll))
        # 更新视图起始位置
        self.current_x_start = new_start
        # 更新视图
        self.current_xlim = (new_start, new_start + self.view_width)
        self.ax.set_xlim(self.current_x_start, self.current_x_start + self.view_width)

        self.canvas.draw_idle()

    def on_x_scroll(self, *args):
        """处理水平滚动事件"""
        if not hasattr(self, 'xmax_total') or self.xmax_total <= self.view_width:
            return  # 无数据或无需滚动时直接返回

        event_type = args[0]
        max_scroll = self.xmax_total - self.view_width  # 最大可滚动范围

        # 解析滚动类型
        if event_type == "moveto":
            # 拖动滑块事件：args[1] 是滑块位置比例 (0.0~1.0)
            fraction = float(args[1])
            new_start = fraction * max_scroll
        elif event_type == "scroll":
            # 点击箭头事件：args[1] 是滚动步长 (1=左移，-1=右移)
            step = int(args[1])
            new_start = self.current_x_start + step * 200  # 每次滚动200单位
        else:
            return

        # 限制滚动范围
        new_start = max(0, min(new_start, max_scroll))

        # 更新视图参数
        if new_start != self.current_x_start:
            self.current_x_start = new_start
            self.ax.set_xlim(new_start, new_start + self.view_width)
            self.canvas.draw_idle()

            # 更新滚动条滑块位置
            scroll_span = self.xmax_total - self.view_width
            if scroll_span > 0:
                self.gantt_hscroll.set(
                    new_start / scroll_span,
                    (new_start + self.view_width) / self.xmax_total
                )

    def create_data_table(self, parent):
        """创建数据表格"""
        self.tree = ttk.Treeview(parent, columns=("cast", "charge", "machine", "start", "end"), show="headings")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        # 配置高亮标签样式
        self.tree.tag_configure("highlight", background="#FFE4E1")  # ✅ 正确配置方式
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        # 配置表头
        columns = {
            "cast": "浇次号",
            "charge": "炉次号",
            "machine": "设备号",
            "start": "开始时间",
            "end": "结束时间"
        }
        for col, text in columns.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=80, anchor="center")

        # 绑定点击事件
        self.tree.bind("<<TreeviewSelect>>", self.on_table_select)

    # ----------------- 数据操作相关方法 -----------------
    def load_settings(self):
        """加载配置文件"""
        try:
            with open("Data/setting.json") as f:
                self.settings = json.load(f)
                for key, entry in self.entries.items():
                    entry.delete(0, tk.END)
                    entry.insert(0, str(self.settings.get(key, "")))
        except Exception as e:
            messagebox.showerror("错误", f"无法读取配置文件:\n{str(e)}")

    def save_settings(self):
        """保存配置文件"""
        try:
            for key, entry in self.entries.items():
                self.settings[key] = int(entry.get())

            with open("Data/setting.json", "w") as f:
                json.dump(self.settings, f, indent=4)

            messagebox.showinfo("成功", "配置保存成功")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败:\n{str(e)}")

    def load_result(self):
        """加载结果数据"""
        try:
            with open("Data/SCC_RES/result.json") as f:
                data = json.load(f)
                self.result_data = data.get("block", [])
                self.start_time = data.get("start_time", 0)
                # 获取设备列表
                machines = sorted({item["machine"] for item in self.result_data})
                self.total_machines = len(machines)  # ✅ 初始化 total_machines
                # 配置滚动条
                if self.total_machines > self.visible_machines:
                    self.gantt_vscroll.configure(command=self.on_y_scroll)
                else:
                    self.gantt_vscroll.configure(command=None)
                # 计算数据总长度
                self.xmax_total = max(
                    (item["end"] - self.start_time for item in self.result_data),
                    default=0
                )
                # 配置滚动条
                max_scroll = max(0, self.xmax_total - self.view_width)
                # 计算滚动条滑块比例\
                if max_scroll > 0:
                    self.gantt_hscroll.set(0, self.view_width / self.xmax_total)
                else:
                    self.gantt_hscroll.set(0, 1)  # 数据不足一屏时禁用
                self.gantt_hscroll.set(0, self.view_width / self.xmax_total if self.xmax_total > 0 else 1)
                # 初始化高亮状态
                for item in self.result_data:
                    item["highlight"] = False
                # 更新视图
                self.update_gantt()
                self.update_table()

        except Exception as e:
            messagebox.showerror("错误", f"无法读取结果文件:\n{str(e)}")

    # ----------------- 程序执行控制 -----------------
    def run_program(self):
        """执行主程序"""
        if self.process and self.process.poll() is None:
            messagebox.showwarning("警告", "程序已在运行中")
            return

        try:
            # 创建日志窗口
            self.create_log_window()

            # 启动子进程
            self.process = subprocess.Popen(
                "main.exe",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                shell=True
            )

            # 启动日志读取线程
            self.log_thread = threading.Thread(
                target=self.read_output,
                daemon=True
            )
            self.log_thread.start()

        except Exception as e:
            self.log_queue.put(f"\n错误: {str(e)}\n")
            self.stop_btn.config(state=tk.DISABLED)

    def read_output(self):
        """读取程序输出到队列"""
        while True:
            output = self.process.stdout.readline()
            if output == '' and self.process.poll() is not None:
                break
            if output:
                self.log_queue.put(output)

        # 程序结束处理
        return_code = self.process.poll()
        if return_code != 0:
            self.log_queue.put(f"\n程序异常退出，返回码: {return_code}\n")
        else:
            self.log_queue.put("\n程序执行完成\n")

        # 禁用中止按钮
        self.stop_btn.config(state=tk.DISABLED)

    def stop_program(self):
        """中止程序执行"""
        if self.process and self.process.poll() is None:
            try:
                if os.name == 'nt':
                    subprocess.run(f"taskkill /F /PID {self.process.pid}", shell=True)
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.log_queue.put("\n已发送中止信号...\n")
            except Exception as e:
                self.log_queue.put(f"\n中止失败: {str(e)}\n")

    def stop_program(self):
        if self.process is None or self.process.poll() is not None:
            messagebox.showinfo("提示", "没有正在运行的程序")
            return

        try:
            if os.name == 'nt':
                # 终止进程树
                subprocess.run(
                    f"taskkill /F /T /PID {self.process.pid}",
                    shell=True,
                    check=True
                )
            else:
                os.kill(self.process.pid, signal.SIGTERM)

            # 等待进程终止，避免状态误判
            self.process.wait(timeout=5)
            messagebox.showinfo("提示", "程序已中止")
            self.process = None

        except subprocess.TimeoutExpired:
            messagebox.showerror("错误", "中止失败：进程未在指定时间内终止")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("错误", f"中止失败（命令执行错误）:\n{str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"中止失败:\n{str(e)}")

    # ----------------- 可视化更新方法 -----------------
    def update_gantt(self):
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 使用微软雅黑
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        """更新甘特图"""
        self.ax.clear()
        # 获取设备子集
        machines = sorted({item["machine"] for item in self.result_data})
        visible_machines = machines[self.current_ypos: self.current_ypos + self.visible_machines]
        # 设置Y轴范围
        self.ax.set_ylim(0.5, self.visible_machines + 0.5)
        self.ax.set_yticks(range(1, self.visible_machines + 1))
        self.ax.set_yticklabels([f"设备 {m}" for m in visible_machines])
        # 设置视图范围
        if hasattr(self, 'current_xlim'):
            start = self.current_xlim[0]
        else:
            start = 0  # 初始位置
        # 设置刻度（根据需求调整步长）
        self.ax.set_xticks(np.arange(0, self.xmax_total + 2000, 2000))
        # 同步视图范围
        current_start = self.ax.get_xlim()[0] if hasattr(self, 'current_xlim') else 0
        current_start = (current_start // 2000) * 2000  # 对齐到2000倍数
        self.ax.set_xlim(self.current_x_start, self.current_x_start + self.view_width)
        # 设置颜色映射
        charges = list(set(item["charge"] for item in self.result_data))
        colors = matplotlib.cm.get_cmap('tab20', len(charges))
        color_map = {charge: colors(i) for i, charge in enumerate(charges)}

        # 绘制每个任务块
        # 绘制每个任务块
        for item in self.result_data:
            machine_idx = machines.index(item["machine"]) + 1
            start = item["start"] - self.start_time
            duration = item["end"] - item["start"]

            # 增强高亮样式
            if item["highlight"]:
                facecolor = (1, 0.5, 0.5, 0.7)  # 半透明红色
                edgecolor = (1, 0, 0, 1)  # 纯红色
                linewidth = 3
                hatch = "////"  # 添加斜线图案
            else:
                facecolor = color_map[item["charge"]]
                edgecolor = 'black'
                linewidth = 0.5
                hatch = None

            rect = Rectangle(
                (start, machine_idx - 0.45),
                duration,
                0.9,
                facecolor=facecolor,
                edgecolor=edgecolor,
                linewidth=linewidth,
                hatch=hatch,  # 添加纹理
                zorder=2 if item["highlight"] else 1  # 高亮项在上层
            )
            self.ax.add_patch(rect)
        # 设置图表样式
        self.ax.set_xlabel("时间（分钟）")
        self.ax.grid(True, axis='x', linestyle='--')
        self.fig.tight_layout()
        # ... 绘制逻辑不变 ...
        self.canvas.draw()

    def update_table(self):
        """更新数据表格"""
        # 定义高亮样式
        style = ttk.Style()
        style.configure("Highlight.Treeview", background="#FFE4E1")  # 浅红色背景

        for item in self.tree.get_children():
            self.tree.delete(item)

        for item in self.result_data:
            values = (
                item["cast"],
                item["charge"],
                item["machine"],
                item["start"],
                item["end"]
            )
            # 通过 tags 参数应用标签
            tags = ("highlight",) if item["highlight"] else ()
            self.tree.insert("", "end", values=values, tags=tags)

    # ----------------- 交互事件处理 -----------------
    def on_table_select(self, event):
        """表格选中事件"""
        selected = self.tree.selection()
        if not selected:
            return

        item_id = selected[0]
        item_index = self.tree.index(item_id)
        self.result_data[item_index]["highlight"] ^= True  # 切换高亮状态

        self.update_gantt()
        self.update_table()

class DataManagementModule(tk.Frame):
    """数据管理模块"""

    class DynamicFormDialog(tk.Toplevel):
        """动态表单生成器"""

        def __init__(self, parent, fields):
            super().__init__(parent)
            self.result = None
            self.entries = {}

            for idx, field in enumerate(fields):
                ttk.Label(self, text=f"{field}:").grid(row=idx, column=0)
                entry = ttk.Entry(self)
                entry.grid(row=idx, column=1)
                self.entries[field] = entry

            ttk.Button(self, text="保存", command=self.on_save).grid(row=len(fields), columnspan=2)

        def on_save(self):
            self.result = [entry.get() for entry in self.entries.values()]
            self.destroy()
    def __init__(self, parent):
        super().__init__(parent)
        # 新增数据库连接
        self.db_conn = sqlite3.connect(
            'steel_production.db',
            check_same_thread=False
        )
        print("数据库绝对路径:", os.path.abspath("steel_production.db"))
        self.search_config = {
            "production": {
                "fields": ["order_no", "furnace_no", "status"],
                "labels": ["订单号", "炉号", "状态"]
            },
            "cast_plan": {
                "fields": ["heat_id", "cast_no", "order_no"],
                "labels": ["任务号", "浇次号", "合同号"]
            },
            "contract": {
                "fields": ["FURNACE_NO", "CONTRACT_NO"],
                "labels": ["炉号", "合同号"]
            },
            "steel_result": {
                "fields": ["machine", "cast", "charge"],
                "labels": ["设备号", "浇次", "炉次"]
            }
        }
        # 添加SQL日志追踪（关键调试代码）
        self.table_var = tk.StringVar()
        self.table_var.trace_add("write", self.on_table_changed)  # 添加状态监听
        self.db_conn.set_trace_callback(print)
        self.current_table = "production"  # 当前显示表
        self.table_config = {
            "production": {"type": "db", "title": "生产数据表"},
            "cast_plan": {"type": "db", "title": "浇次计划结果表"},
            "contract": {"type": "xml", "file": "FurnaceResult2.xml"},
            "steel_result": {"type": "json", "file": "Data/result.json"}
        }
        self.create_ui()
        self.init_tables()

    def on_table_changed(self, event=None):
        """当前表变化时更新数据和按钮状态"""
        # 获取最新选择值（关键！）
        self.current_table = self.table_var.get()
        print(f"当前表已切换至：{self.current_table}")
        self.load_current_data()

    def __del__(self):
        """析构时关闭连接"""
        if hasattr(self, 'db_conn'):
            self.db_conn.close()

    def create_ui(self):
        """创建带表切换功能的界面"""
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", pady=5)
        search_frame = ttk.Frame(control_frame)
        search_frame.pack(side="left", padx=10)
        # 初始化时设置有效值
        self.table_var = tk.StringVar(value="production")  # 设置默认值
        # 搜索字段选择
        self.search_field = ttk.Combobox(
            search_frame,
            state="readonly",
            width=8
        )
        self.search_field.pack(side="left")

        # 关键词输入
        self.search_entry = ttk.Entry(search_frame, width=15)
        self.search_entry.pack(side="left", padx=2)

        # 搜索按钮
        ttk.Button(
            search_frame,
            text="搜索",
            command=self.execute_search
        ).pack(side="left")

        # 清空按钮
        ttk.Button(
            search_frame,
            text="清空",
            command=self.clear_search
        ).pack(side="left", padx=2)

        # 绑定表切换事件
        self.table_var.trace_add("write", self.update_search_fields)
        table_selector = ttk.Combobox(
            control_frame,
            textvariable=self.table_var,
            values=list(self.table_config.keys()),  # 确保值列表正确
            state="readonly"
        )
        table_selector.pack(side="left", padx=5)
        table_selector.bind("<<ComboboxSelected>>", self.on_table_changed)

        # 操作按钮组
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="刷新", command=self.load_current_data).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="添加", command=self.add_record).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_record).pack(side="left", padx=2)

        # 数据表格
        self.tree = ttk.Treeview(self, columns=(), show="headings")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

    def update_search_fields(self, *args):
        """切换表时更新搜索字段选项"""
        current_table = self.table_var.get()
        config = self.search_config.get(current_table, {})
        self.search_field["values"] = config.get("labels", [])
        if config.get("labels"):
            self.search_field.current(0)

    def execute_search(self):
        """执行搜索（增加字段校验）"""
        current_table = self.table_var.get()
        keyword = self.search_entry.get().strip()

        # 获取当前表配置
        config = self.search_config.get(current_table, {})
        labels = config.get("labels", [])
        fields = config.get("fields", [])

        # 验证字段映射
        if len(labels) != len(fields):
            messagebox.showerror("配置错误", "字段标签与字段名数量不匹配")
            return

        # 获取选中字段
        selected_label = self.search_field.get()
        try:
            field_index = labels.index(selected_label)
            field_name = fields[field_index]  # 正确获取字段名
        except (ValueError, IndexError):
            messagebox.showerror("错误", "无效的搜索字段")
            return

        # 分数据源处理
        if self.table_config[current_table]["type"] == "db":
            self._search_db(current_table, field_name, keyword)
        else:
            self._search_file_data(current_table, field_name, keyword)

    def _search_db(self, table_name, field, keyword):
        """数据库表搜索"""
        with sqlite3.connect('steel_production.db') as conn:
            cursor = conn.cursor()
            query = f"SELECT * FROM {table_name} WHERE {field} LIKE ?"
            cursor.execute(query, (f"%{keyword}%",))

            # 清空并更新表格
            self.tree.delete(*self.tree.get_children())
            for row in cursor.fetchall():
                self.tree.insert("", "end", values=row)

    def _search_file_data(self, table_name, field, keyword):
        """文件数据搜索"""
        if table_name == "contract":
            self._search_xml(field, keyword)
        elif table_name == "steel_result":
            self._search_json(field, keyword)

    def _search_xml(self, field, keyword):
        """XML精确搜索（适配NewDataSet结构）"""
        self.tree.delete(*self.tree.get_children())

        try:
            dom = minidom.parse("FurnaceResult2.xml")
            # 关键修正1：定位父节点
            new_dataset = dom.getElementsByTagName("NewDataSet")[0]
            records = new_dataset.getElementsByTagName("FurnaceResult")
        except Exception as e:
            messagebox.showerror("XML错误", f"文件解析失败: {str(e)}")
            return

        # 关键修正2：匹配实际存在的字段
        valid_fields = {node.tagName for record in records
                        for node in record.childNodes if node.nodeType == node.ELEMENT_NODE}
        if field not in valid_fields:
            messagebox.showerror("搜索错误", f"字段[{field}]不存在于XML数据中")
            return

        clean_keyword = keyword.strip()
        for record in records:
            try:
                # 关键修正3：带错误保护的节点访问
                target_node = record.getElementsByTagName(field)[0]
                field_value = target_node.firstChild.data.strip() if target_node.firstChild else ""

                if field_value == clean_keyword:
                    # 动态获取所有字段值
                    values = []
                    for node in record.childNodes:
                        if node.nodeType == node.ELEMENT_NODE:
                            value = node.firstChild.data.strip() if node.firstChild else ""
                            values.append(value)
                    self.tree.insert("", "end", values=values)
            except IndexError:
                continue  # 跳过没有该字段的记录

    def _search_json(self, field, keyword):
        """JSON精确搜索（严格字段匹配）"""
        self.tree.delete(*self.tree.get_children())
        try:
            with open("Data/result.json") as f:
                data = json.load(f)

            clean_keyword = keyword.strip()
            for block in data.get("block", []):
                # 严格匹配字段名称
                if field not in block:
                    continue

                value = str(block[field]).strip()
                if value == clean_keyword:
                    self.tree.insert("", "end", values=(
                        block.get("machine", ""),
                        block.get("start", ""),
                        block.get("end", ""),
                        block.get("cast", ""),
                        block.get("charge", "")
                    ))
        except Exception as e:
            messagebox.showerror("错误", f"JSON搜索失败: {str(e)}")

    def clear_search(self):
        """清空搜索条件"""
        self.search_entry.delete(0, "end")
        self.load_current_data()

    # ----------------- 通用数据操作 -----------------
    def load_current_data(self):
        """加载当前表数据"""
        """加载数据前完全重置表格"""
        # 清空数据和列定义
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = []

        # 根据当前表类型加载
        table = self.table_var.get()
        config = self.table_config.get(table, {})
        if config.get("type") == "db":
            self.load_db_table(table)
        elif config["type"] == "xml":
            self.load_xml_data()
        elif config["type"] == "json":
            self.load_json_data()

        # ----------------- 数据库表操作 -----------------

    def delete_record(self):
        """统一删除记录入口"""
        selected = self.tree.selection()
        if not selected:
            return

        current_table = self.table_var.get()
        table_type = self.table_config[current_table]["type"]

        if table_type == "db":
            self._delete_db_record(selected)
        elif table_type == "xml":
            self._delete_xml_record(selected)
        elif table_type == "json":
            self._delete_json_record(selected)
            return

    def _delete_db_record(self, selected_items):
        """删除数据库记录（动态识别主键）"""
        try:
            with sqlite3.connect('steel_production.db') as conn:
                cursor = conn.cursor()

                # 获取当前表的主键字段名
                cursor.execute(f"PRAGMA table_info({self.current_table})")
                columns = cursor.fetchall()
                pk_column = next((col[1] for col in columns if col[5] == 1), None)

                if not pk_column:
                    raise ValueError(f"表 {self.current_table} 没有主键或主键不明确")

                # 获取选中记录的主键值
                pk_values = []
                for item_id in selected_items:
                    item = self.tree.item(item_id)
                    # 主键值在values中的位置对应表结构
                    pk_index = [col[0] for col in columns].index(0)  # cid从0开始
                    pk_values.append(str(item['values'][pk_index]))

                # 批量删除
                placeholders = ",".join(["?"] * len(pk_values))
                cursor.execute(
                    f"DELETE FROM {self.current_table} WHERE {pk_column} IN ({placeholders})",
                    pk_values
                )
                conn.commit()

            self.load_current_data()
        except StopIteration:
            messagebox.showerror("错误", "无法识别表的主键")
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"删除失败: {str(e)}")

    def load_db_table(self, table_name):
        """加载数据库表"""
        self.tree.delete(*self.tree.get_children())
        with sqlite3.connect('steel_production.db') as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]

            # 配置表格列
            self.tree["columns"] = columns
            for col in columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=100)

            # 加载数据
            cursor.execute(f"SELECT * FROM {table_name}")
            for row in cursor.fetchall():
                self.tree.insert("", "end", values=row)

    # ----------------- XML表操作 -----------------
    def load_xml_data(self):
        """加载XML合同数据"""
        self.tree.delete(*self.tree.get_children())
        dom = minidom.parse("FurnaceResult2.xml")
        records = dom.getElementsByTagName("FurnaceResult")

        # 动态获取字段
        sample = records[0] if records else []
        columns = [node.tagName for node in sample.childNodes if node.nodeType == node.ELEMENT_NODE]

        # 配置表格
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        # 插入数据
        for record in records:
            values = [node.firstChild.data if node.firstChild else ""
                      for node in record.childNodes if node.nodeType == node.ELEMENT_NODE]
            self.tree.insert("", "end", values=values)


    # ----------------- JSON表操作 -----------------
    def load_json_data(self):
        """加载JSON数据（固定列顺序）"""
        try:
            with open("Data/result.json") as f:
                data = json.load(f)

            # 显式定义列顺序（与JSON字段顺序严格一致）
            columns = ["machine", "start", "end", "cast", "charge", "type"]

            # 配置表格列
            self.tree["columns"] = columns
            for col in columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=100)

            for block in data.get("block", []):
                values = [block.get(col, "") for col in columns]
                print(f"Debug - 提取值: {values}")  # 添加调试输出
                self.tree.insert("", "end", values=values)
            # 按定义顺序插入数据
            for block in data.get("block", []):
                values = [block.get(col, "") for col in columns]
                self.tree.insert("", "end", values=values)

        except Exception as e:
            messagebox.showerror("加载错误", f"JSON数据加载失败: {str(e)}")


    def init_tables(self):
        """初始化数据库表结构"""
        with sqlite3.connect('steel_production.db') as conn:
            cursor = conn.cursor()
            # 浇次计划结果表
            cursor.execute('''CREATE TABLE IF NOT EXISTS cast_plan
                            (heat_id TEXT PRIMARY KEY,
                             cast_no TEXT,
                             charge_no TEXT,
                             order_no TEXT,
                             min_length INTEGER,
                             max_length INTEGER)''')
            # 生产数据表（原有）
            cursor.execute('''CREATE TABLE IF NOT EXISTS production
                            (id INTEGER PRIMARY KEY,
                             order_no TEXT,
                             furnace_no TEXT UNIQUE,
                             width INTEGER,
                             status TEXT)''')
            conn.commit()

    def create_table(self):
        """创建数据库表"""
        cursor = self.db_conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS production_data
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         order_no TEXT NOT NULL,
                         furnace_no TEXT UNIQUE,
                         width INTEGER,
                         status TEXT CHECK(status IN ('计划', '进行中', '已完成')))''')
        self.db_conn.commit()

    def load_data(self, condition=None):
        """加载数据到表格"""
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 执行查询
        cursor = self.db_conn.cursor()
        query = "SELECT * FROM production_data"
        params = ()

        if condition:
            query += " WHERE " + condition
            params = (f"%{self.search_entry.get()}%",)

        cursor.execute(query, params)

        # 插入数据
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def show_add_dialog(self):
        """显示添加记录对话框（增加类型检查）"""
        current_table = self.table_var.get()
        table_type = self.table_config[current_table]["type"]

        # 非数据库类型直接提示
        if table_type != "db":
            messagebox.showerror("操作禁止", "非数据库表不允许直接修改，请通过文件操作更新数据")
            return

        # 数据库表才显示对话框
        dialog = tk.Toplevel(self)
        dialog.title(f"添加记录 - {current_table}")

        # 根据表结构生成字段
        fields = self._get_table_fields(current_table)

        entries = {}
        for idx, (label, field) in enumerate(fields):
            ttk.Label(dialog, text=label + ":").grid(row=idx, column=0, padx=5, pady=2)
            entry = ttk.Entry(dialog)
            entry.grid(row=idx, column=1, padx=5, pady=2)
            entries[field] = entry

        # 动态生成特殊控件
        if current_table == "cast_plan":
            # 浇次计划表不需要状态选择框
            ttk.Button(dialog, text="保存",
                       command=lambda: self.save_record(current_table, entries, dialog, fields)
                       ).grid(row=len(fields), columnspan=2)
        else:
            # 生产数据表需要状态选择
            status_combo = ttk.Combobox(dialog, values=["计划", "进行中", "已完成"])
            status_combo.grid(row=len(fields), column=1)
            entries["status"] = status_combo
            ttk.Button(dialog, text="保存",
                       command=lambda: self.save_record(current_table, entries, dialog, fields)
                       ).grid(row=len(fields) + 1, columnspan=2)

    def _get_table_fields(self, table_name):
        """根据表名获取字段配置"""
        field_map = {
            "cast_plan": [
                ("任务号", "heat_id"),
                ("浇次号", "cast_no"),
                ("炉次号", "charge_no"),
                ("合同号", "order_no"),
                ("最小长度", "min_length"),
                ("最大长度", "max_length"),
            ],
            "production": [
                ("订单号", "order_no"),
                ("炉号", "furnace_no"),
                ("重量（吨）", "weight"),
                ("宽度（mm）", "width")
            ]
        }
        return field_map.get(table_name, [])

    def save_record(self, table_name, entries, dialog, fields):
        """动态生成SQL保存记录"""
        try:
            cursor = self.db_conn.cursor()

            # 生成列名和值列表
            columns = [field[1] for field in fields]
            values = []

            # 类型转换处理
            type_rules = {
                "cast_plan": {
                    "min_length": int,
                    "max_length": int
                },
                "production": {
                    "weight": float,
                    "width": int
                }
            }

            for col in columns:
                value = entries[col].get()
                # 应用类型转换规则
                if table_name in type_rules and col in type_rules[table_name]:
                    convert_func = type_rules[table_name][col]
                    values.append(convert_func(value))
                else:
                    values.append(value)

            # 动态生成插入语句
            placeholders = ",".join(["?"] * len(values))
            if table_name == "cast_plan":
                sql = f"""INSERT INTO {table_name} 
                        (heat_id, cast_no, charge_no, order_no, min_length, max_length)
                        VALUES ({placeholders})"""
            else:
                # 处理生产表的状态字段
                values.append(entries["status"].get())
                columns.append("status")
                placeholders += ",?"
                sql = f"""INSERT INTO {table_name} 
                        ({','.join(columns)}) VALUES ({placeholders})"""

            cursor.execute(sql, values)
            self.db_conn.commit()

            # 刷新数据
            self.load_current_data()
            dialog.destroy()
            messagebox.showinfo("成功", "记录添加成功")

        except ValueError as e:
            messagebox.showerror("输入错误", f"数据类型错误：{str(e)}")
        except sqlite3.IntegrityError as e:
            messagebox.showerror("唯一性冲突", f"主键或唯一约束冲突：{str(e)}")
        except Exception as e:
            messagebox.showerror("数据库错误", f"保存失败：{str(e)}")

    def add_record(self):
        """根据当前表类型执行添加操作"""
        table_type = self.table_config[self.current_table]["type"]
        if table_type == "db":
            self._add_db_record()
        elif table_type == "xml":
            self._add_xml_record()
        elif table_type == "json":
            self._add_json_record()

    def _add_db_record(self):
        """添加数据库记录"""
        dialog = tk.Toplevel(self)
        dialog.title("添加新记录")

        # 根据当前表获取字段信息
        with sqlite3.connect('steel_production.db') as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = [col[1] for col in cursor.fetchall() if col[1] != 'id']

        entries = {}
        for idx, col in enumerate(columns):
            ttk.Label(dialog, text=f"{col}:").grid(row=idx, column=0, padx=5, pady=2)
            entry = ttk.Entry(dialog)
            entry.grid(row=idx, column=1, padx=5, pady=2)
            entries[col] = entry

        ttk.Button(dialog, text="保存",
                   command=lambda: self._save_db_record(dialog, entries, columns)).grid(row=len(columns), columnspan=2)

    def _save_db_record(self, dialog, entries, columns):
        """保存数据库记录"""
        try:
            with sqlite3.connect('steel_production.db') as conn:
                cursor = conn.cursor()
                values = [entries[col].get() for col in columns]
                placeholders = ",".join(["?"] * len(values))

                # 处理不同表的插入语句
                if self.current_table == "cast_plan":
                    sql = f'''INSERT OR REPLACE INTO {self.current_table} 
                            (heat_id, cast_no, charge_no, order_no, min_length, max_length)
                            VALUES (?,?,?,?,?,?)'''
                else:
                    sql = f"INSERT INTO {self.current_table} ({','.join(columns)}) VALUES ({placeholders})"

                cursor.execute(sql, values)
                conn.commit()
                self.load_current_data()
                dialog.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    # ----------------- XML 数据操作 -----------------
    def _add_xml_record(self):
        """添加XML炉次记录"""
        dialog = tk.Toplevel(self)
        dialog.title("添加新炉次记录")

        # 根据示例数据结构生成字段
        fields = [
            "SM_DIV", "HR_DIV", "FURNACE_NO",
            "FURNACE_AVAILABLE_CC_LIST", "ORDER_AVAILABLE_CC_LIST",
            "FURNACE_WT", "IS_FULL", "ORDER_NO", "IS_NECESSARY_ORDER",
            "ORDER_DELIVY_DATE_TYPE_PRIORITY", "ORDER_DELIVERY_TIME_PRIORITY",
            "IS_FURNACE_WIDTH_JUMP", "FURNACE_WIDTH_MAX", "FURNACE_WIDTH_MIN",
            "ORDER_WIDTH_MAX", "ORDER_WIDTH_MIN", "SLAB_NUM", "SLAB_PRE_WT",
            "SLAB_TOTAL_WT", "ORDER_FINAL_DEST", "ST_NO_SPEC", "REFINE_DIV",
            "LG_ST", "SLAB_DEST", "IS_RH_DEEP", "RH_OR_LF", "UNIT_MAJOR"
        ]

        entries = {}
        for idx, field in enumerate(fields):
            ttk.Label(dialog, text=f"{field}:").grid(row=idx, column=0, padx=2, pady=2)
            entry = ttk.Entry(dialog)
            entry.grid(row=idx, column=1, padx=2, pady=2)
            entries[field] = entry

        ttk.Button(dialog, text="保存", command=lambda: self._save_xml_record(dialog, entries)).grid(row=len(fields)+1, columnspan=2)

    def _save_xml_record(self, dialog, entries):
        """保存XML记录"""
        try:
            dom = minidom.parse("FurnaceResult2.xml")
            new_dataset = dom.getElementsByTagName("NewDataSet")[0]

            # 创建新节点
            new_result = dom.createElement("FurnaceResult")
            for field, entry in entries.items():
                elem = dom.createElement(field)
                elem.appendChild(dom.createTextNode(entry.get()))
                new_result.appendChild(elem)

            new_dataset.appendChild(new_result)

            # 保持XML格式
            with open("FurnaceResult2.xml", "w", encoding="utf-8") as f:
                dom.writexml(f, indent="  ", addindent="  ", newl="\n")

            self.load_current_data()
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def _add_json_record(self):
        """添加JSON炼钢结果"""
        dialog = tk.Toplevel(self)
        dialog.title("添加炼钢结果")

        fields = ["machine", "start", "end", "cast", "charge"]
        entries = {}

        for idx, field in enumerate(fields):
            ttk.Label(dialog, text=f"{field}:").grid(row=idx, column=0, padx=5, pady=2)
            entry = ttk.Entry(dialog)
            entry.grid(row=idx, column=1, padx=5, pady=2)
            entries[field] = entry

        ttk.Button(dialog, text="保存", command=lambda: self._save_json_record(dialog, entries)).grid(row=len(fields),
                                                                                                      columnspan=2)

    def _save_json_record(self, dialog, entries):
        """保存JSON记录"""
        try:
            with open("Data/result.json", "r+") as f:
                data = json.load(f)

                # 构建新记录
                new_block = {
                    "type": "main",
                    "machine": int(entries["machine"].get()),
                    "start": int(entries["start"].get()),
                    "end": int(entries["end"].get()),
                    "cast": int(entries["cast"].get()),
                    "charge": int(entries["charge"].get())
                }

                data["block"].append(new_block)

                # 保持原有结构
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()

            self.load_current_data()
            dialog.destroy()
        except ValueError:
            messagebox.showerror("输入错误", "数值字段必须为整数")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def update_record(self, record_id, entries, dialog):
        """更新数据库记录"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''UPDATE production SET
                            order_no = ?,
                            furnace_no = ?,
                            weight = ?,
                            width = ?,
                            status = ?
                            WHERE id = ?''',
                           (entries["order_no"].get(),
                            entries["furnace_no"].get(),
                            float(entries["weight"].get()),
                            int(entries["width"].get()),
                            entries["status"].get(),
                            record_id))
            self.db_conn.commit()
            self.load_data()
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"更新失败: {str(e)}")

    def _delete_xml_record(self, selected_items):
        """删除XML记录"""
        try:
            dom = minidom.parse("FurnaceResult2.xml")
            new_dataset = dom.getElementsByTagName("NewDataSet")[0]
            records = new_dataset.getElementsByTagName("FurnaceResult")

            # 获取选中记录的索引
            indexes = [int(self.tree.index(item)) for item in selected_items]

            # 逆序删除
            for idx in sorted(indexes, reverse=True):
                node = records[idx]
                new_dataset.removeChild(node)

            # 保存修改
            with open("FurnaceResult2.xml", "w", encoding="utf-8") as f:
                dom.writexml(f, indent="  ", addindent="  ", newl="\n")

            self.load_current_data()
        except Exception as e:
            messagebox.showerror("错误", f"删除失败: {str(e)}")

    def _delete_json_record(self, selected_items):
        """删除JSON记录"""
        try:
            with open("Data/result.json", "r+") as f:
                data = json.load(f)
                indexes = [int(self.tree.index(item)) for item in selected_items]

                # 逆序删除
                for idx in sorted(indexes, reverse=True):
                    del data["block"][idx]

                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()

            self.load_current_data()
        except Exception as e:
            messagebox.showerror("错误", f"删除失败: {str(e)}")
    def search_data(self):
        """执行搜索"""
        field_map = {
            "订单号": "order_no",
            "炉号": "furnace_no"
        }

        field = field_map.get(self.search_field.get(), "order_no")
        keyword = self.search_entry.get()

        if keyword:
            self.load_data(f"{field} LIKE ?")
        else:
            self.load_data()

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("钢铁生产管理系统")
        self.geometry("800x600")

        # 初始化样式
        self.init_style()

        # 创建标签页容器
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both")

        # 初始化各模块
        self.create_modules()

    def init_style(self):
        """初始化界面样式"""
        style = ttk.Style()
        # 标签页样式
        style.configure("TNotebook", background="#F0F0F0")
        style.configure("TNotebook.Tab",
                        font=('微软雅黑', 10),
                        padding=[10, 5],
                        background="#E1E1E1",
                        foreground="#444444")
        style.map("TNotebook.Tab",
                  background=[("selected", "#4B8BBE")],)

    def create_modules(self):
        """创建三个模块并设置不同配色方案"""
        # 模块1：组炉组浇（蓝色系）
        # 组炉组浇模块（蓝色系）
        self.module1 = FurnacePlanningModule(self.notebook)
        self.notebook.add(self.module1, text="组炉组浇")

        # 模块2：炼钢连铸（绿色系）
        self.module2 = SteelCastingModule(self.notebook)
        self.notebook.add(self.module2, text="炼钢连铸")

        # 模块3：数据管理（橙色系）
        # 数据管理模块（新实现）
        self.module3 = DataManagementModule(self.notebook)
        self.notebook.add(self.module3, text="数据管理")

class ModuleBase(tk.Frame):
    """带颜色的模块基类"""

    def __init__(self, parent, title, bg_color="#FFFFFF", text_color="#333333"):
        super().__init__(parent)
        self.canvas = None
        self.title = title
        self.bg_color = bg_color
        self.text_color = text_color
        self.configure(background=bg_color)
        self.create_widgets()

    def create_widgets(self):
        """创建界面组件"""
        # 模块标题
        label = tk.Label(self,
                         text=self.title,
                         font=("微软雅黑", 16, "bold"),
                         fg=self.text_color,
                         bg=self.bg_color)
        label.pack(pady=20)

        # 开发状态提示
        status = tk.Label(self,
                          text="等待开发...",
                          font=("微软雅黑", 12),
                          fg="gray",
                          bg=self.bg_color)
        status.pack(pady=10)

        # 预留扩展区域（带轻微阴影效果）
        self.content = tk.Frame(self,
                                bg=self.bg_color,
                                highlightbackground="#DDDDDD",
                                highlightthickness=1)
        self.content.pack(expand=True, fill="both", padx=20, pady=10)


if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()