import tkinter as tk
from tkinter import ttk, messagebox
import json
import matplotlib
import numpy as np
import os
import signal
import subprocess
import threading
import queue

from matplotlib import pyplot as plt

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

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
        params = ["Mode", "Diff", "time_limit"]
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