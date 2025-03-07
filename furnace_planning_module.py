import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sqlite3
import xml.etree.ElementTree as ET
import signal
import threading
import subprocess
from xml.dom import minidom

class FurnacePlanningModule(tk.Frame):
    """组炉组浇模块"""
    def __init__(self, parent):
        super().__init__(parent)
        self.log_window = None  # 新增日志窗口引用
        self.log_text = None    # 日志文本框
        self.stop_flag = False  # 中止标志
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
        """运行程序并显示日志窗口"""
        if self.process and self.process.poll() is None:
            messagebox.showwarning("警告", "程序已在运行中")
            return

        # 创建日志窗口
        self._create_log_window()
        self.stop_flag = False

        try:
            # 启动子进程并捕获输出流
            self.process = subprocess.Popen("furnacePlan.exe",
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            shell=True,
                                            text=True,
                                            bufsize=1,  # 行缓冲模式
                                            encoding='utf-8')

            # 启动日志监控线程
            threading.Thread(target=self._monitor_output, daemon=True).start()
        except Exception as e:
            messagebox.showerror("错误", f"程序启动失败: {str(e)}")
            self._close_log_window()

    def _create_log_window(self):
        """创建日志显示窗口"""
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.destroy()

        self.log_window = tk.Toplevel(self)
        self.log_window.title("程序运行日志")
        self.log_window.geometry("800x500")

        # 日志文本框
        text_frame = ttk.Frame(self.log_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_text = tk.Text(text_frame, wrap="word", state="disabled")
        scrolly = ttk.Scrollbar(text_frame, command=self.log_text.yview)
        scrollx = ttk.Scrollbar(text_frame, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)

        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrolly.grid(row=0, column=1, sticky="ns")
        scrollx.grid(row=1, column=0, sticky="ew")
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        # 中止按钮
        btn_frame = ttk.Frame(self.log_window)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="中止运行", command=self._stop_from_log_window).pack()

        # 窗口关闭事件处理
        self.log_window.protocol("WM_DELETE_WINDOW", self._close_log_window)

    def _monitor_output(self):
        """监控进程输出的线程方法"""
        while self.process.poll() is None and not self.stop_flag:
            # 实时读取输出
            line = self.process.stdout.readline()
            if line:
                self._append_log(line.strip())

        # 进程结束后处理
        self._append_log("\n进程已结束" if not self.stop_flag else "\n进程已被中止")
        self.process = None

    def _append_log(self, text):
        """安全更新日志文本框"""

        def update():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", text + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        self.log_text.after(0, update)

    def _stop_from_log_window(self):
        """从日志窗口触发中止"""
        self.stop_furnace_plan()
        self.stop_flag = True
        self._append_log("用户请求中止...")

    def stop_furnace_plan(self):
        """增强中止方法"""
        if self.process is None or self.process.poll() is not None:
            return

        try:
            if os.name == 'nt':
                # Windows系统发送终止信号
                self.process.send_signal(signal.CTRL_C_EVENT)
            else:
                # 其他系统发送SIGTERM
                self.process.terminate()

            # 等待进程结束
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        except Exception as e:
            messagebox.showerror("错误", f"中止失败: {str(e)}")

    def _close_log_window(self):
        """安全关闭日志窗口"""
        if self.log_window:
            self.log_window.destroy()
            self.log_window = None

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
