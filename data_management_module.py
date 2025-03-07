import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sqlite3
from xml.dom import minidom

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
    # [原DataManagementModule类的完整代码]
    # 注意保留所有数据库操作方法
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
