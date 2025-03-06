# main.py
import signal
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import subprocess
import os
import matplotlib
import numpy as np
from matplotlib import pyplot as plt
import xml.etree.ElementTree as ET
from tkinter import ttk

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
        """创建带颜色的XML数据展示"""
        canvas = tk.Canvas(parent, bg="white")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=canvas.xview)

        self.input_frame = ttk.Frame(canvas)
        self.input_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self.input_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

    def load_input_data(self):
        """加载并展示FurnaceResult数据"""
        try:
            tree = ET.parse("FurnaceResult2.xml")
            root = tree.getroot()

            # 清空现有数据
            for widget in self.input_frame.winfo_children():
                widget.destroy()

            # 创建带颜色的数据行
            for idx, result in enumerate(root.findall("FurnaceResult")):
                frame = ttk.Frame(self.input_frame)
                frame.grid(row=idx, column=0, sticky="ew", pady=2)

                # 设置交替背景色
                bg_color = "#F0F8FF" if idx % 2 == 0 else "#E0FFFF"
                frame.configure(style="Custom.TFrame")
                style = ttk.Style()
                style.configure("Custom.TFrame", background=bg_color)

                # 显示关键字段
                ttk.Label(frame, text=f"炉号: {result.find('FURNACE_NO').text}",
                          background=bg_color).pack(side="left", padx=10)
                ttk.Label(frame, text=f"板坯数: {result.find('SLAB_NUM').text}",
                          background=bg_color).pack(side="left", padx=10)
                ttk.Label(frame, text=f"重量: {result.find('FURNACE_WT').text}吨",
                          background=bg_color).pack(side="left", padx=10)

        except Exception as e:
            messagebox.showerror("错误", f"加载XML数据失败: {str(e)}")

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
        self.configure(background="#E8F5E9")
        self.process = None
        self.highlight_items = set()  # 存储高亮项的ID
        # 正确初始化顺序
        self.create_widgets()      # 先创建子控件
        self.setup_gantt_interaction()  # 再设置交互
        self.load_settings()
        self.load_result()
        self.process = None

    def setup_gantt_interaction(self):
        """设置图表交互事件"""
        # 绑定到 matplotlib canvas
        self.canvas.mpl_connect("button_press_event", self.on_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_release_event", self.on_release)

        # 初始化交互状态
        self.zoom_rect = None
        self.press_start = None
        self.xlim = self.ax.get_xlim()

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
        """创建甘特图画布"""
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.gantt_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def create_data_table(self, parent):
        """创建数据表格"""
        self.tree = ttk.Treeview(parent, columns=("cast", "charge", "machine", "start", "end"), show="headings")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
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

                # 添加高亮状态
                for item in self.result_data:
                    item["highlight"] = False

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
            self.process = subprocess.Popen("main.exe", shell=True)
        except Exception as e:
            messagebox.showerror("错误", f"程序启动失败:\n{str(e)}")

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

        # 获取机器列表
        machines = sorted({item["machine"] for item in self.result_data})
        y_ticks = [i + 1 for i in range(len(machines))]
        self.ax.set_yticks(y_ticks)
        self.ax.set_yticklabels([f"设备 {m}" for m in machines])
        # 计算时间范围
        xmin = min(item["start"] - self.start_time for item in self.result_data)
        xmax = max(item["end"] - self.start_time for item in self.result_data)

        # 设置坐标轴范围
        self.ax.set_ylim(0.5, len(machines) + 0.5)  # 增加垂直缩进
        self.ax.set_xlim(xmin - 50, xmax + 50)  # 增加水平缩进
        # 设置刻度步长（关键修改）
        self.ax.set_xticks(np.arange(xmin // 100 * 100, xmax + 100, 100))  # 100单位间隔
        # 设置颜色映射
        charges = list(set(item["charge"] for item in self.result_data))
        colors = matplotlib.cm.get_cmap('tab20', len(charges))
        color_map = {charge: colors(i) for i, charge in enumerate(charges)}

        # 绘制每个任务块
        for item in self.result_data:
            machine_idx = machines.index(item["machine"]) + 1
            start = item["start"] - self.start_time
            duration = item["end"] - item["start"]
            # 根据高亮状态设置颜色

            rect = Rectangle(
                (start, machine_idx - 0.45),  # y位置微调
                duration,
                0.9,  # 高度从0.8增大到0.9
                facecolor=color_map[item["charge"]],
                edgecolor='red' if item["highlight"] else 'black',
                linewidth=2 if item["highlight"] else 0.5
            )
            self.ax.add_patch(rect)
        # 设置图表样式
        self.ax.set_xlabel("时间（分钟）")
        self.ax.grid(True, axis='x', linestyle='--')
        self.fig.tight_layout()
        # self.canvas.draw()

    def update_table(self):
        """更新数据表格"""
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
            self.tree.insert("", "end", values=values, tags=("highlight" if item["highlight"] else ""))

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

    # ----------------- 事件处理函数 -----------------
    def on_press(self, event):
        """鼠标按下事件"""
        if event.inaxes != self.ax:
            return
        if event.button == 1:  # 左键按下
            self.press_start = (event.xdata, event.ydata)
            self.zoom_rect = Rectangle((0, 0), 0, 0,
                                       linestyle='--',
                                       edgecolor='gray',
                                       facecolor=(0.8, 0.8, 0.8, 0.5))
            self.ax.add_patch(self.zoom_rect)
            self.canvas.draw()

    def on_motion(self, event):
        """鼠标拖动事件"""
        if self.zoom_rect is None or event.inaxes != self.ax:
            return
        # 更新矩形框位置
        start_x, start_y = self.press_start
        curr_x = event.xdata
        curr_y = event.ydata

        width = curr_x - start_x
        height = curr_y - start_y

        self.zoom_rect.set_width(width)
        self.zoom_rect.set_height(height * 10)  # 垂直方向铺满
        self.zoom_rect.set_xy((start_x, self.ax.get_ylim()[0]))
        self.canvas.draw()

    def on_release(self, event):
        """鼠标释放事件"""
        if self.zoom_rect is None:
            return

        # 获取缩放范围
        start_x = self.press_start[0]
        end_x = event.xdata

        # 调整坐标轴范围
        self.ax.set_xlim(sorted([start_x, end_x]))

        # 清理临时图形
        self.zoom_rect.remove()
        self.zoom_rect = None
        self.press_start = None

        # 重绘图表
        self.canvas.draw()

        # 双击右键恢复原始视图
        if event.button == 3 and event.dblclick:
            self.ax.set_xlim(self.xlim)
            self.canvas.draw()

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
        self.module3 = ModuleBase(self.notebook,
                                  "数据管理模块",
                                  bg_color="#FFF3E0",
                                  text_color="#EF6C00")
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