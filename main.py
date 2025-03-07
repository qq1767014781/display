import tkinter as tk
from tkinter import ttk
from furnace_planning_module import FurnacePlanningModule
from steel_casting_module import SteelCastingModule
from data_management_module import DataManagementModule

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("钢铁生产管理系统")
        self.geometry("800x600")
        self.init_style()
        self.create_modules()

    def init_style(self):
        """初始化界面样式"""
        style = ttk.Style()
        # [原MainApplication的样式配置代码]

    def create_modules(self):
        """创建三大功能模块"""
        self.notebook = ttk.Notebook(self)
        # [原模块创建代码]
        self.notebook.add(FurnacePlanningModule(self.notebook), text="组炉组浇")
        self.notebook.add(SteelCastingModule(self.notebook), text="炼钢连铸")
        self.notebook.add(DataManagementModule(self.notebook), text="数据管理")
        self.notebook.pack(expand=True, fill="both")

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()