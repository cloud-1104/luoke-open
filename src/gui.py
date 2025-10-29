"""
GUI界面
使用Tkinter实现的配置和执行界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import io
import os
import sys
import time
from datetime import datetime
from PIL import Image, ImageTk
from src.config_manager import ConfigManager
from src.redeemer import RedeemController
from src.logger import LoggerManager


def get_resource_path(relative_path):
    """获取资源文件的绝对路径(支持打包后的路径)"""
    try:
        # PyInstaller创建临时文件夹,路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class RockKingdomGUI:
    """洛克王国自动激活GUI界面"""

    def __init__(self):
        """初始化GUI"""
        self.root = tk.Tk()
        self.root.title("洛克王国自动激活工具")
        self.root.geometry("900x700")
        self.root.resizable(False, False)

        # 初始化配置管理器
        self.config_manager = ConfigManager()
        try:
            self.config_manager.load()
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {e}")

        # 日志管理器
        self.logger = LoggerManager()

        # 验证码相关
        self.captcha_window = None
        self.captcha_input_var = tk.StringVar()
        self.captcha_ready_event = threading.Event()

        # 暂停标志
        self.stop_flag = threading.Event()

        # 定时启动相关
        self.scheduler_thread = None
        self.schedule_stop_event = threading.Event()

        # Cookie池存储(完整Cookie字符串)
        self.full_cookies = []

        # 创建界面
        self._create_widgets()
        self._load_config_to_ui()

    def _center_window(self, window):
        """居中窗口 - 消除所有窗口位置的特殊情况"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

    def _create_widgets(self):
        """创建界面组件"""
        # 创建笔记本(选项卡)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 配置选项卡
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="配置")
        self._create_config_tab(config_frame)

        # 执行选项卡
        execute_frame = ttk.Frame(notebook)
        notebook.add(execute_frame, text="执行")
        self._create_execute_tab(execute_frame)

        # 交流群选项卡
        community_frame = ttk.Frame(notebook)
        notebook.add(community_frame, text="交流群")
        self._create_community_tab(community_frame)

    def _create_config_tab(self, parent):
        """创建配置选项卡"""
        # 版权水印
        watermark_label = ttk.Label(
            parent,
            text="本软件为免费开源，如果你是购买获得请申请退款或投诉 | 作者: OP",
            font=("Arial", 10, "bold"),
            foreground="red",
            background="yellow"
        )
        watermark_label.pack(fill=tk.X, padx=10, pady=5)

        # 创建主容器，使用三列布局
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # === 左列：小程序配置 ===
        left_frame = ttk.LabelFrame(main_frame, text="小程序配置", padding=10)
        left_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)

        # 小程序验证开关
        self.use_miniapp_auth_var = tk.BooleanVar()
        ttk.Checkbutton(left_frame, text="启用小程序验证 (默认关闭，使用公开接口)",
                       variable=self.use_miniapp_auth_var,
                       command=self._toggle_miniapp_auth).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        # 小程序Authorization
        ttk.Label(left_frame, text="Authorization:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.miniapp_auth_entry = ttk.Entry(left_frame, width=35, state=tk.DISABLED)
        self.miniapp_auth_entry.grid(row=2, column=0, pady=2)

        # 小程序Data参数
        ttk.Label(left_frame, text="Data参数:").grid(row=3, column=0, sticky=tk.W, pady=(10, 2))
        self.miniapp_data_text = scrolledtext.ScrolledText(left_frame, width=35, height=3, state=tk.DISABLED)
        self.miniapp_data_text.grid(row=4, column=0, pady=2)
        ttk.Label(left_frame, text="(必须包含req_path=/api/home/index)",
                  font=("", 7), foreground="gray").grid(row=5, column=0, sticky=tk.W)

        # 公告关键字
        ttk.Label(left_frame, text="公告关键字:").grid(row=6, column=0, sticky=tk.W, pady=(10, 2))

        # 自动计算开关
        self.auto_keyword_var = tk.BooleanVar()
        ttk.Checkbutton(left_frame, text="自动计算 (根据活动开始日期)",
                       variable=self.auto_keyword_var,
                       command=self._toggle_auto_keyword).grid(row=7, column=0, sticky=tk.W, pady=2)

        # 关键词前缀
        keyword_prefix_frame = ttk.Frame(left_frame)
        keyword_prefix_frame.grid(row=8, column=0, sticky=tk.W, pady=2)
        ttk.Label(keyword_prefix_frame, text="前缀:").pack(side=tk.LEFT, padx=(0, 2))
        self.keyword_prefix_entry = ttk.Entry(keyword_prefix_frame, width=10)
        self.keyword_prefix_entry.pack(side=tk.LEFT, padx=2)
        self.keyword_prefix_entry.insert(0, "Day")

        # 活动开始日期
        date_frame = ttk.Frame(left_frame)
        date_frame.grid(row=9, column=0, sticky=tk.W, pady=2)
        ttk.Label(date_frame, text="活动开始:").pack(side=tk.LEFT, padx=(0, 2))

        # 年月日选择器 (默认 2025-10-24)
        self.start_year_spinbox = ttk.Spinbox(date_frame, from_=2020, to=2030, width=6, format="%04.0f")
        self.start_year_spinbox.pack(side=tk.LEFT, padx=2)
        self.start_year_spinbox.set(2025)
        ttk.Label(date_frame, text="年").pack(side=tk.LEFT)

        self.start_month_spinbox = ttk.Spinbox(date_frame, from_=1, to=12, width=4, format="%02.0f")
        self.start_month_spinbox.pack(side=tk.LEFT, padx=2)
        self.start_month_spinbox.set(10)
        ttk.Label(date_frame, text="月").pack(side=tk.LEFT)

        self.start_day_spinbox = ttk.Spinbox(date_frame, from_=1, to=31, width=4, format="%02.0f")
        self.start_day_spinbox.pack(side=tk.LEFT, padx=2)
        self.start_day_spinbox.set(24)
        ttk.Label(date_frame, text="日").pack(side=tk.LEFT)

        # 手动输入框
        self.keyword_entry = ttk.Entry(left_frame, width=35)
        self.keyword_entry.grid(row=10, column=0, pady=2)

        # 计算结果显示
        self.keyword_calc_label = ttk.Label(left_frame, text="", font=("", 8), foreground="blue")
        self.keyword_calc_label.grid(row=11, column=0, sticky=tk.W)

        ttk.Label(left_frame, text="(手动模式示例: Day1, Day2...)",
                  font=("", 7), foreground="gray").grid(row=12, column=0, sticky=tk.W)

        # === 中列：Cookie池管理 ===
        middle_frame = ttk.LabelFrame(main_frame, text="Cookie池管理", padding=10)
        middle_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=5, pady=5)

        # Cookie列表框
        list_frame = ttk.Frame(middle_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.cookie_listbox = tk.Listbox(list_frame, width=40, height=10, yscrollcommand=scrollbar.set)
        self.cookie_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.cookie_listbox.yview)

        # Cookie操作按钮
        cookie_btn_frame = ttk.Frame(middle_frame)
        cookie_btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(cookie_btn_frame, text="添加", command=self._add_cookie, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(cookie_btn_frame, text="删除", command=self._remove_cookie, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(cookie_btn_frame, text="清空", command=self._clear_cookies, width=10).pack(side=tk.LEFT, padx=2)

        ttk.Label(middle_frame, text="(每个Cookie一个账号，程序会并发兑换)",
                  font=("", 7), foreground="gray").pack(pady=(5, 0))

        # === 右列：运行参数 ===
        right_frame = ttk.LabelFrame(main_frame, text="运行参数", padding=10)
        right_frame.grid(row=0, column=2, sticky=tk.NSEW, padx=5, pady=5)

        # 验证码选项
        ttk.Label(right_frame, text="验证码识别:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ocr_var = tk.BooleanVar()
        ocr_frame = ttk.Frame(right_frame)
        ocr_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(ocr_frame, text="手动", variable=self.ocr_var, value=False).pack(side=tk.LEFT)
        ttk.Radiobutton(ocr_frame, text="OCR", variable=self.ocr_var, value=True).pack(side=tk.LEFT, padx=10)

        # OCR重试次数
        ttk.Label(right_frame, text="OCR重试次数:").grid(row=2, column=0, sticky=tk.W, pady=(5, 2))
        self.ocr_retries_spinbox = ttk.Spinbox(right_frame, from_=1, to=10, width=15)
        self.ocr_retries_spinbox.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.ocr_retries_spinbox.set(3)

        # 兑换重试次数
        ttk.Label(right_frame, text="兑换重试次数:").grid(row=4, column=0, sticky=tk.W, pady=(5, 2))
        self.redeem_retries_spinbox = ttk.Spinbox(right_frame, from_=1, to=20, width=15)
        self.redeem_retries_spinbox.grid(row=5, column=0, sticky=tk.W, pady=2)
        self.redeem_retries_spinbox.set(5)

        # 请求线程数
        ttk.Label(right_frame, text="请求线程数:").grid(row=6, column=0, sticky=tk.W, pady=(5, 2))
        self.threads_spinbox = ttk.Spinbox(right_frame, from_=1, to=50, width=15)
        self.threads_spinbox.grid(row=7, column=0, sticky=tk.W, pady=2)
        self.threads_spinbox.set(10)

        # 请求超时时间
        ttk.Label(right_frame, text="请求超时(秒):").grid(row=8, column=0, sticky=tk.W, pady=(5, 2))
        self.timeout_spinbox = ttk.Spinbox(right_frame, from_=1, to=30, width=15)
        self.timeout_spinbox.grid(row=9, column=0, sticky=tk.W, pady=2)
        self.timeout_spinbox.set(5)

        # 轮询间隔时间
        ttk.Label(right_frame, text="轮询间隔(秒):").grid(row=10, column=0, sticky=tk.W, pady=(5, 2))
        self.poll_interval_spinbox = ttk.Spinbox(right_frame, from_=0.1, to=30.0, increment=0.1, width=15)
        self.poll_interval_spinbox.grid(row=11, column=0, sticky=tk.W, pady=2)
        self.poll_interval_spinbox.set(1.0)

        # 配置主框架的列权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)

        # === 底部：代理配置 ===
        proxy_frame = ttk.LabelFrame(parent, text="代理设置 (仅用于网页端请求)", padding=10)
        proxy_frame.pack(fill=tk.X, padx=15, pady=10)

        # 代理开关
        self.use_proxy_var = tk.BooleanVar()
        ttk.Checkbutton(proxy_frame, text="启用代理", variable=self.use_proxy_var,
                       command=self._toggle_proxy_inputs).pack(side=tk.LEFT, padx=5)

        # 代理主机
        ttk.Label(proxy_frame, text="主机:").pack(side=tk.LEFT, padx=(20, 5))
        self.proxy_host_entry = ttk.Entry(proxy_frame, width=25)
        self.proxy_host_entry.pack(side=tk.LEFT, padx=5)

        # 代理端口
        ttk.Label(proxy_frame, text="端口:").pack(side=tk.LEFT, padx=(10, 5))
        self.proxy_port_spinbox = ttk.Spinbox(proxy_frame, from_=1, to=65535, width=10)
        self.proxy_port_spinbox.pack(side=tk.LEFT, padx=5)

        # 保存按钮
        save_btn = ttk.Button(parent, text="保存配置", command=self._save_config, width=15)
        save_btn.pack(pady=10)

    def _create_execute_tab(self, parent):
        """创建执行选项卡"""
        # 版权水印
        watermark_label = ttk.Label(
            parent,
            text="本软件为免费开源，如果你是购买获得请申请退款或投诉 | 作者: OP",
            font=("Arial", 10, "bold"),
            foreground="red",
            background="yellow"
        )
        watermark_label.pack(fill=tk.X, padx=10, pady=5)

        # 状态显示
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(status_frame, text="执行状态:", font=("", 10)).pack(side=tk.LEFT, padx=(0, 10))
        self.status_label = ttk.Label(status_frame, text="就绪", foreground="green", font=("", 10, "bold"))
        self.status_label.pack(side=tk.LEFT)

        # 按钮区域
        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=10)

        self.start_btn = ttk.Button(button_frame, text="开始执行", command=self._start_execution, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="暂停执行", command=self._stop_execution, state=tk.DISABLED, width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(button_frame, text="清空日志", command=self._clear_log, width=15)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # 定时启动区域
        schedule_frame = ttk.LabelFrame(parent, text="定时启动 (设置今天的启动时间)", padding=10)
        schedule_frame.pack(fill=tk.X, padx=10, pady=5)

        # 时间选择器
        time_input_frame = ttk.Frame(schedule_frame)
        time_input_frame.pack(side=tk.LEFT, padx=5)

        ttk.Label(time_input_frame, text="时:").pack(side=tk.LEFT, padx=2)
        self.hour_spinbox = ttk.Spinbox(time_input_frame, from_=0, to=23, width=5, format="%02.0f")
        self.hour_spinbox.pack(side=tk.LEFT, padx=2)
        self.hour_spinbox.set("00")

        ttk.Label(time_input_frame, text="分:").pack(side=tk.LEFT, padx=2)
        self.minute_spinbox = ttk.Spinbox(time_input_frame, from_=0, to=59, width=5, format="%02.0f")
        self.minute_spinbox.pack(side=tk.LEFT, padx=2)
        self.minute_spinbox.set("00")

        ttk.Label(time_input_frame, text="秒:").pack(side=tk.LEFT, padx=2)
        self.second_spinbox = ttk.Spinbox(time_input_frame, from_=0, to=59, width=5, format="%02.0f")
        self.second_spinbox.pack(side=tk.LEFT, padx=2)
        self.second_spinbox.set("00")

        # 定时启动按钮
        self.schedule_btn = ttk.Button(schedule_frame, text="启用定时", command=self._toggle_schedule, width=12)
        self.schedule_btn.pack(side=tk.LEFT, padx=10)

        # 定时状态显示
        self.schedule_status_label = ttk.Label(schedule_frame, text="", foreground="gray", font=("", 9))
        self.schedule_status_label.pack(side=tk.LEFT, padx=5)

        # 日志显示
        log_frame = ttk.LabelFrame(parent, text="执行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, width=100, height=25, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_community_tab(self, parent):
        """创建交流群选项卡"""
        # 版权水印
        watermark_label = ttk.Label(
            parent,
            text="本软件为免费开源，如果你是购买获得请申请退款或投诉 | 作者: OP",
            font=("Arial", 10, "bold"),
            foreground="red",
            background="yellow"
        )
        watermark_label.pack(fill=tk.X, padx=10, pady=10)

        # 标题
        title_label = ttk.Label(
            parent,
            text="洛克王国交流群【1群】",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(30, 10))

        # 副标题
        subtitle_label = ttk.Label(
            parent,
            text="扫描下方二维码加入微信群，与其他玩家交流经验",
            font=("", 11)
        )
        subtitle_label.pack(pady=(0, 20))

        # 二维码图片
        try:
            qr_image_path = get_resource_path("docs/群聊.jpg")
            qr_image = Image.open(qr_image_path)
            # 保持原始尺寸或稍微缩放以确保清晰度
            qr_image = qr_image.resize((300, 420), Image.Resampling.LANCZOS)
            qr_photo = ImageTk.PhotoImage(qr_image)
            qr_label = ttk.Label(parent, image=qr_photo)
            qr_label.image = qr_photo  # 保持引用防止被垃圾回收
            qr_label.pack(pady=20)
        except Exception as e:
            error_label = ttk.Label(
                parent,
                text=f"二维码加载失败: {e}",
                foreground="red",
                font=("", 12)
            )
            error_label.pack(pady=20)

        # 提示信息
        tip_label = ttk.Label(
            parent,
            text="该二维码7天内(11月3日前)有效，重新进入将更新",
            font=("", 9),
            foreground="gray"
        )
        tip_label.pack(pady=(10, 20))

    def _load_config_to_ui(self):
        """加载配置到界面"""
        # 加载小程序验证开关
        use_miniapp_auth = self.config_manager.get("use_miniapp_auth", False)
        self.use_miniapp_auth_var.set(use_miniapp_auth)

        # 临时启用输入框以插入值
        self.miniapp_auth_entry.config(state=tk.NORMAL)
        self.miniapp_data_text.config(state=tk.NORMAL)

        self.miniapp_auth_entry.insert(0, self.config_manager.get("miniapp_authorization", ""))

        # 加载Data参数
        miniapp_data = self.config_manager.get("miniapp_data", "")
        self.miniapp_data_text.insert("1.0", miniapp_data)

        # 根据开关状态启用/禁用输入框
        self._toggle_miniapp_auth()

        # 加载Cookie列表
        self.full_cookies = self.config_manager.get("web_cookies", [])
        self.cookie_listbox.delete(0, tk.END)
        for cookie in self.full_cookies:
            # 截取Cookie前60个字符用于显示
            display_text = cookie[:60] + "..." if len(cookie) > 60 else cookie
            self.cookie_listbox.insert(tk.END, display_text)

        # 加载关键词配置 (默认启用自动计算)
        self.auto_keyword_var.set(self.config_manager.get("auto_keyword", True))
        self.keyword_prefix_entry.delete(0, tk.END)
        self.keyword_prefix_entry.insert(0, self.config_manager.get("keyword_prefix", "Day"))

        # 加载活动开始日期 (默认 2025-10-24)
        activity_start_date = self.config_manager.get("activity_start_date", "2025-10-24")
        try:
            start_date = datetime.strptime(activity_start_date, "%Y-%m-%d")
            self.start_year_spinbox.set(start_date.year)
            self.start_month_spinbox.set(start_date.month)
            self.start_day_spinbox.set(start_date.day)
        except ValueError:
            # 如果解析失败,使用固定默认值
            self.start_year_spinbox.set(2025)
            self.start_month_spinbox.set(10)
            self.start_day_spinbox.set(24)

        # 如果是手动模式,加载保存的关键词
        # 如果是自动模式,将由 _toggle_auto_keyword() 计算并设置
        if not self.auto_keyword_var.get():
            self.keyword_entry.insert(0, self.config_manager.get("announcement_keyword", "Day1"))

        # 应用自动计算状态
        self._toggle_auto_keyword()

        self.ocr_var.set(self.config_manager.get("use_ocr", True))  # 默认使用OCR
        self.ocr_retries_spinbox.set(self.config_manager.get("ocr_max_retries", 3))
        self.redeem_retries_spinbox.set(self.config_manager.get("redeem_max_retries", 5))
        self.threads_spinbox.set(self.config_manager.get("request_threads", 10))
        self.timeout_spinbox.set(self.config_manager.get("request_timeout", 5))
        self.poll_interval_spinbox.set(self.config_manager.get("poll_interval", 1.0))

        # 加载代理配置
        self.use_proxy_var.set(self.config_manager.get("use_proxy", False))
        self.proxy_host_entry.insert(0, self.config_manager.get("proxy_host", ""))
        self.proxy_port_spinbox.set(self.config_manager.get("proxy_port", 0))
        self._toggle_proxy_inputs()  # 根据代理开关状态更新输入框状态

    def _save_config(self):
        """保存配置到文件"""
        try:
            self.config_manager.set("use_miniapp_auth", self.use_miniapp_auth_var.get())

            # 临时启用输入框以获取值
            auth_state = str(self.miniapp_auth_entry['state'])
            data_state = str(self.miniapp_data_text['state'])

            self.miniapp_auth_entry.config(state=tk.NORMAL)
            self.miniapp_data_text.config(state=tk.NORMAL)

            self.config_manager.set("miniapp_authorization", self.miniapp_auth_entry.get())

            # 获取并验证Data参数
            miniapp_data = self.miniapp_data_text.get("1.0", tk.END).strip()
            self.config_manager.set("miniapp_data", miniapp_data)

            # 恢复原状态
            self.miniapp_auth_entry.config(state=auth_state)
            self.miniapp_data_text.config(state=data_state)

            self.config_manager.set("web_cookies", self.full_cookies)  # 保存完整Cookie列表

            # 保存关键词配置
            self.config_manager.set("auto_keyword", self.auto_keyword_var.get())
            self.config_manager.set("keyword_prefix", self.keyword_prefix_entry.get())

            # 保存活动开始日期
            try:
                year = int(self.start_year_spinbox.get())
                month = int(self.start_month_spinbox.get())
                day = int(self.start_day_spinbox.get())
                start_date = datetime(year, month, day).strftime("%Y-%m-%d")
                self.config_manager.set("activity_start_date", start_date)
            except ValueError:
                pass

            # 保存关键词(手动或自动计算后的值)
            keyword_state = str(self.keyword_entry['state'])
            self.keyword_entry.config(state=tk.NORMAL)
            self.config_manager.set("announcement_keyword", self.keyword_entry.get())
            self.keyword_entry.config(state=keyword_state)

            self.config_manager.set("use_ocr", self.ocr_var.get())
            self.config_manager.set("ocr_max_retries", int(self.ocr_retries_spinbox.get()))
            self.config_manager.set("redeem_max_retries", int(self.redeem_retries_spinbox.get()))
            self.config_manager.set("request_threads", int(self.threads_spinbox.get()))
            self.config_manager.set("request_timeout", int(self.timeout_spinbox.get()))
            self.config_manager.set("poll_interval", float(self.poll_interval_spinbox.get()))

            # 保存代理配置
            self.config_manager.set("use_proxy", self.use_proxy_var.get())
            self.config_manager.set("proxy_host", self.proxy_host_entry.get())
            self.config_manager.set("proxy_port", int(self.proxy_port_spinbox.get()))

            self.config_manager.save()
            messagebox.showinfo("成功", "配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")

    def _toggle_miniapp_auth(self):
        """根据小程序验证开关状态启用/禁用相关输入框"""
        if self.use_miniapp_auth_var.get():
            # 启用小程序验证时启用输入框
            self.miniapp_auth_entry.config(state=tk.NORMAL)
            self.miniapp_data_text.config(state=tk.NORMAL)
        else:
            # 禁用小程序验证时禁用输入框
            self.miniapp_auth_entry.config(state=tk.DISABLED)
            self.miniapp_data_text.config(state=tk.DISABLED)

    def _toggle_proxy_inputs(self):
        """根据代理开关状态启用/禁用代理输入框"""
        if self.use_proxy_var.get():
            # 启用代理时启用输入框
            self.proxy_host_entry.config(state=tk.NORMAL)
            self.proxy_port_spinbox.config(state=tk.NORMAL)
        else:
            # 禁用代理时禁用输入框
            self.proxy_host_entry.config(state=tk.DISABLED)
            self.proxy_port_spinbox.config(state=tk.DISABLED)

    def _start_execution(self):
        """开始执行兑换流程"""
        # 同步UI中的关键词到配置对象(自动计算模式下keyword_entry会被自动更新)
        keyword_state = str(self.keyword_entry['state'])
        self.keyword_entry.config(state=tk.NORMAL)
        self.config_manager.set("announcement_keyword", self.keyword_entry.get())
        self.keyword_entry.config(state=keyword_state)

        # 验证配置
        valid, error_msg = self.config_manager.validate()
        if not valid:
            messagebox.showerror("配置错误", error_msg)
            return

        # 重置暂停标志
        self.stop_flag.clear()

        # 禁用开始按钮,启用暂停按钮
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._update_status("执行中...", "orange")
        self._clear_log()

        # 在新线程中执行,避免阻塞GUI
        thread = threading.Thread(target=self._execute_redeem, daemon=True)
        thread.start()

    def _stop_execution(self):
        """暂停执行"""
        self.stop_flag.set()
        self._update_status("已暂停", "red")
        self._append_log("\n[系统] 用户请求暂停执行")
        self.stop_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.NORMAL)

    def _execute_redeem(self):
        """执行兑换流程(在后台线程)"""
        try:
            controller = RedeemController(self.config_manager)

            # 执行兑换
            result = controller.execute(
                progress_callback=self._update_progress,
                captcha_callback=self._show_captcha_input,
                stop_flag=self.stop_flag  # 传递暂停标志
            )

            # 显示结果
            if result["success"]:
                self._update_status("执行成功", "green")
                self._append_log(f"\n✓ {result['message']}")
            else:
                self._update_status("执行失败", "red")
                self._append_log(f"\n✗ {result['message']}")

        except Exception as e:
            self._update_status("执行异常", "red")
            self._append_log(f"\n✗ 异常: {e}")
        finally:
            # 重新启用开始按钮,禁用暂停按钮
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

    def _update_progress(self, message: str):
        """更新进度信息"""
        self._append_log(f"[进度] {message}")

    def _update_status(self, text: str, color: str):
        """更新状态标签"""
        self.root.after(0, lambda: self.status_label.config(text=text, foreground=color))

    def _append_log(self, message: str):
        """追加日志到文本框"""
        def _append():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

        self.root.after(0, _append)

    def _clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _show_captcha_input(self, image_data: bytes, ocr_result: str = "") -> str:
        """
        显示验证码输入窗口(仅手动模式)

        Args:
            image_data: 验证码图片字节数据
            ocr_result: OCR识别结果(如果有,用于OCR失败后的降级)

        Returns:
            用户输入或确认的验证码
        """
        # 重置事件
        self.captcha_ready_event.clear()
        self.captcha_input_var.set("")

        # 在主线程显示窗口
        self.root.after(0, lambda: self._create_captcha_window(image_data, ocr_result))

        # 等待用户输入
        self.captcha_ready_event.wait()

        result = self.captcha_input_var.get()
        return result

    def _create_captcha_window(self, image_data: bytes, ocr_result: str = ""):
        """创建验证码输入窗口"""
        if self.captcha_window:
            self.captcha_window.destroy()

        self.captcha_window = tk.Toplevel(self.root)
        self.captcha_window.title("输入验证码")
        self.captcha_window.geometry("400x300")
        self.captcha_window.resizable(False, False)
        self.captcha_window.grab_set()  # 模态窗口
        self._center_window(self.captcha_window)

        # 显示验证码图片
        try:
            image = Image.open(io.BytesIO(image_data))
            # 放大图片便于查看
            image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            img_label = ttk.Label(self.captcha_window, image=photo)
            img_label.image = photo  # 保持引用
            img_label.pack(pady=10)
        except Exception as e:
            ttk.Label(self.captcha_window, text=f"图片加载失败: {e}").pack(pady=10)

        # 提示文本
        if ocr_result:
            ttk.Label(
                self.captcha_window,
                text=f"OCR识别结果: {ocr_result} (可修改后提交)",
                font=("", 10),
                foreground="blue"
            ).pack(pady=5)
        else:
            ttk.Label(self.captcha_window, text="请输入验证码:").pack(pady=5)

        # 输入框
        entry = ttk.Entry(self.captcha_window, width=20, font=("", 14))
        entry.pack(pady=5)
        if ocr_result:
            entry.insert(0, ocr_result)  # 预填充OCR结果
        entry.focus()
        entry.select_range(0, tk.END)  # 全选文本

        # 提交按钮
        def submit():
            captcha = entry.get().strip()
            if not captcha:
                messagebox.showwarning("警告", "验证码不能为空")
                return
            self.captcha_input_var.set(captcha)
            self.captcha_window.destroy()
            self.captcha_ready_event.set()

        submit_btn = ttk.Button(self.captcha_window, text="提交", command=submit)
        submit_btn.pack(pady=10)

        # 绑定回车键
        entry.bind("<Return>", lambda e: submit())

    def _add_cookie(self):
        """添加Cookie - 选择扫码或手动输入"""
        # 创建选择对话框
        choice_dialog = tk.Toplevel(self.root)
        choice_dialog.title("添加Cookie")
        choice_dialog.geometry("450x250")
        choice_dialog.resizable(False, False)
        choice_dialog.grab_set()
        self._center_window(choice_dialog)

        ttk.Label(choice_dialog, text="请选择添加方式:", font=("", 12)).pack(pady=20)

        # 按钮框架
        btn_frame = ttk.Frame(choice_dialog)
        btn_frame.pack(pady=10)

        # QQ扫码登录按钮
        def choose_qq_qr():
            choice_dialog.destroy()
            self._add_cookie_by_qr()

        ttk.Button(btn_frame, text="QQ扫码登录", command=choose_qq_qr, width=15).pack(side=tk.LEFT, padx=5)

        # 微信扫码登录按钮
        def choose_wx_qr():
            choice_dialog.destroy()
            self._add_cookie_by_wx_qr()

        ttk.Button(btn_frame, text="微信扫码登录", command=choose_wx_qr, width=15).pack(side=tk.LEFT, padx=5)

        # 手动输入按钮
        def choose_manual():
            choice_dialog.destroy()
            self._add_cookie_manually()

        ttk.Button(btn_frame, text="手动输入", command=choose_manual, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Label(choice_dialog, text="QQ扫码: 使用手机QQ扫码自动获取Cookie\n微信扫码: 使用微信扫码自动获取Cookie\n手动输入: 从浏览器复制完整Cookie字符串",
                  font=("", 9), foreground="gray", justify=tk.CENTER).pack(pady=10)

    def _add_cookie_by_qr(self):
        """扫码登录获取Cookie"""
        # 创建扫码窗口
        qr_dialog = tk.Toplevel(self.root)
        qr_dialog.title("扫码登录")
        qr_dialog.geometry("500x600")
        qr_dialog.resizable(False, False)
        qr_dialog.grab_set()
        self._center_window(qr_dialog)

        # 标题
        ttk.Label(qr_dialog, text="使用手机QQ扫描二维码", font=("", 14, "bold")).pack(pady=10)

        # 二维码图片容器
        qr_label = ttk.Label(qr_dialog)
        qr_label.pack(pady=10)

        # 状态显示
        status_label = ttk.Label(qr_dialog, text="正在获取二维码...", font=("", 11), foreground="blue")
        status_label.pack(pady=10)

        # 日志显示
        log_frame = ttk.LabelFrame(qr_dialog, text="登录日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        log_text = scrolledtext.ScrolledText(log_frame, width=55, height=10, state=tk.DISABLED)
        log_text.pack(fill=tk.BOTH, expand=True)

        # 取消按钮
        cancel_btn = ttk.Button(qr_dialog, text="取消", command=lambda: qr_dialog.destroy(), width=15)
        cancel_btn.pack(pady=10)

        # 回调函数: 更新日志
        def update_log(message):
            def _update():
                log_text.config(state=tk.NORMAL)
                log_text.insert(tk.END, message + "\n")
                log_text.see(tk.END)
                log_text.config(state=tk.DISABLED)
            qr_dialog.after(0, _update)

        # 回调函数: 显示二维码
        def show_qr(qr_image_bytes):
            def _show():
                try:
                    image = Image.open(io.BytesIO(qr_image_bytes))
                    # 放大二维码便于扫描
                    image = image.resize((300, 300), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    qr_label.config(image=photo)
                    qr_label.image = photo  # 保持引用
                    status_label.config(text="请使用手机QQ扫描二维码", foreground="green")
                except Exception as e:
                    status_label.config(text=f"二维码显示失败: {e}", foreground="red")
            qr_dialog.after(0, _show)

        # 在后台线程执行登录
        def do_login():
            try:
                # 获取代理配置
                proxy = None
                if self.config_manager.get("use_proxy", False):
                    proxy_host = self.config_manager.get("proxy_host", "")
                    proxy_port = self.config_manager.get("proxy_port", 0)
                    if proxy_host and proxy_port:
                        proxy = f"http://{proxy_host}:{proxy_port}"

                # 创建QQLogin实例
                from src.qq_login import QQLogin
                qq_login = QQLogin(proxy=proxy, progress_callback=update_log)

                # 执行登录(传入二维码回调)
                cookie_str = qq_login.login(
                    max_poll_seconds=120,
                    poll_interval=2,
                    qr_callback=show_qr
                )

                # 登录成功,添加Cookie
                def add_success():
                    self.full_cookies.append(cookie_str)
                    display_text = cookie_str[:60] + "..." if len(cookie_str) > 60 else cookie_str
                    self.cookie_listbox.insert(tk.END, display_text)
                    qr_dialog.destroy()
                    messagebox.showinfo("成功", "Cookie已添加,请记得保存配置")

                qr_dialog.after(0, add_success)

            except Exception as e:
                def show_error():
                    status_label.config(text=f"登录失败: {e}", foreground="red")
                    update_log(f"[!] 错误: {e}")
                qr_dialog.after(0, show_error)

        # 启动后台线程
        login_thread = threading.Thread(target=do_login, daemon=True)
        login_thread.start()

    def _add_cookie_by_wx_qr(self):
        """微信扫码登录获取Cookie"""
        # 创建扫码窗口
        qr_dialog = tk.Toplevel(self.root)
        qr_dialog.title("微信扫码登录")
        qr_dialog.geometry("500x600")
        qr_dialog.resizable(False, False)
        qr_dialog.grab_set()
        self._center_window(qr_dialog)

        # 标题
        ttk.Label(qr_dialog, text="使用微信扫描二维码", font=("", 14, "bold")).pack(pady=10)

        # 二维码图片容器
        qr_label = ttk.Label(qr_dialog)
        qr_label.pack(pady=10)

        # 状态显示
        status_label = ttk.Label(qr_dialog, text="正在获取二维码...", font=("", 11), foreground="blue")
        status_label.pack(pady=10)

        # 日志显示
        log_frame = ttk.LabelFrame(qr_dialog, text="登录日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        log_text = scrolledtext.ScrolledText(log_frame, width=55, height=10, state=tk.DISABLED)
        log_text.pack(fill=tk.BOTH, expand=True)

        # 取消按钮
        cancel_btn = ttk.Button(qr_dialog, text="取消", command=lambda: qr_dialog.destroy(), width=15)
        cancel_btn.pack(pady=10)

        # 回调函数: 更新日志
        def update_log(message):
            def _update():
                log_text.config(state=tk.NORMAL)
                log_text.insert(tk.END, message + "\n")
                log_text.see(tk.END)
                log_text.config(state=tk.DISABLED)
            qr_dialog.after(0, _update)

        # 回调函数: 显示二维码
        def show_qr(qr_image_bytes):
            def _show():
                try:
                    image = Image.open(io.BytesIO(qr_image_bytes))
                    # 放大二维码便于扫描
                    image = image.resize((300, 300), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    qr_label.config(image=photo)
                    qr_label.image = photo  # 保持引用
                    status_label.config(text="请使用微信扫描二维码", foreground="green")
                except Exception as e:
                    status_label.config(text=f"二维码显示失败: {e}", foreground="red")
            qr_dialog.after(0, _show)

        # 在后台线程执行登录
        def do_login():
            try:
                # 获取代理配置
                proxy = None
                if self.config_manager.get("use_proxy", False):
                    proxy_host = self.config_manager.get("proxy_host", "")
                    proxy_port = self.config_manager.get("proxy_port", 0)
                    if proxy_host and proxy_port:
                        proxy = f"http://{proxy_host}:{proxy_port}"

                # 创建WeChatLogin实例
                from src.wx_login import WeChatLogin
                wx = WeChatLogin(proxy=proxy)

                # Step 1: 获取二维码
                update_log("[*] 步骤 1: 获取二维码...")
                try:
                    uuid = wx.get_qrcode_page()
                except Exception as e:
                    raise Exception(f"获取二维码页面失败: {e}")

                # Step 2: 获取二维码图片
                update_log("[*] 步骤 2: 获取二维码图片...")
                try:
                    qr_image = wx.get_qrcode_image()
                    show_qr(qr_image)
                except Exception as e:
                    raise Exception(f"获取二维码图片失败: {e}")

                # Step 3: 轮询扫码状态
                update_log("[*] 步骤 3: 等待扫码...")
                max_attempts = 60
                poll_interval = 2

                for attempt in range(1, max_attempts + 1):
                    status = wx.check_scan_status()
                    errcode = status.get('errcode', '')
                    wxcode = status.get('wxcode', '')

                    if errcode == '408':
                        update_log(f"[{attempt}/{max_attempts}] 等待扫码...")
                    elif errcode == '404':
                        update_log("[+] 二维码已扫描，请在手机上确认登录...")
                    elif errcode == '405':
                        update_log("[+] 登录成功!")
                        if wxcode:
                            update_log(f"[+] 获取到 wxcode: {wxcode}")

                            # Step 4: 换取凭证
                            update_log("[*] 步骤 4: 换取 access_token 和 openid...")
                            try:
                                credentials = wx.exchange_code_for_credentials(wxcode)
                            except Exception as e:
                                raise Exception(f"换取凭证失败: {e}")

                            # 构建Cookie字符串
                            cookie_str = (
                                f"acctype=wx; "
                                f"openid={credentials.get('openid')}; "
                                f"access_token={credentials.get('access_token')}; "
                                f"appid=wxfa0c35392d06b82f; "
                                f"ieg_ams_token=; "
                                f"ieg_ams_session_token=; "
                                f"ieg_ams_token_time=; "
                                f"ieg_ams_sign="
                            )

                            # 登录成功,添加Cookie
                            def add_success():
                                self.full_cookies.append(cookie_str)
                                display_text = cookie_str[:60] + "..." if len(cookie_str) > 60 else cookie_str
                                self.cookie_listbox.insert(tk.END, display_text)
                                qr_dialog.destroy()
                                messagebox.showinfo("成功", "Cookie已添加,请记得保存配置")

                            qr_dialog.after(0, add_success)
                            return
                        else:
                            raise Exception("未获取到 wxcode")
                    else:
                        raise Exception(f"未知状态码 {errcode}: {status.get('raw')}")

                    if attempt < max_attempts:
                        time.sleep(poll_interval)

                raise Exception("超时: 二维码未被扫描")

            except Exception as e:
                def show_error():
                    status_label.config(text=f"登录失败: {e}", foreground="red")
                    update_log(f"[!] 错误: {e}")
                qr_dialog.after(0, show_error)

        # 启动后台线程
        login_thread = threading.Thread(target=do_login, daemon=True)
        login_thread.start()

    def _add_cookie_manually(self):
        """手动输入Cookie"""
        # 创建输入窗口
        dialog = tk.Toplevel(self.root)
        dialog.title("手动输入Cookie")
        dialog.geometry("500x200")
        dialog.resizable(False, False)
        dialog.grab_set()
        self._center_window(dialog)

        ttk.Label(dialog, text="请输入完整的Cookie字符串:").pack(pady=10)

        # Cookie输入框
        cookie_text = scrolledtext.ScrolledText(dialog, width=60, height=6)
        cookie_text.pack(padx=10, pady=5)
        cookie_text.focus()

        # 添加按钮
        def add():
            cookie = cookie_text.get("1.0", tk.END).strip()
            if not cookie:
                messagebox.showwarning("警告", "Cookie不能为空")
                return

            # 添加到完整Cookie列表
            self.full_cookies.append(cookie)

            # 更新列表框显示
            display_text = cookie[:60] + "..." if len(cookie) > 60 else cookie
            self.cookie_listbox.insert(tk.END, display_text)

            dialog.destroy()
            messagebox.showinfo("成功", "Cookie已添加,请记得保存配置")

        ttk.Button(dialog, text="添加", command=add).pack(pady=10)


    def _remove_cookie(self):
        """删除选中的Cookie"""
        selection = self.cookie_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的Cookie")
            return

        index = selection[0]

        # 确认删除
        if messagebox.askyesno("确认", "确定要删除选中的Cookie吗?"):
            # 从完整列表和显示列表中删除
            del self.full_cookies[index]
            self.cookie_listbox.delete(index)
            messagebox.showinfo("成功", "Cookie已删除,请记得保存配置")

    def _clear_cookies(self):
        """清空所有Cookie"""
        if not self.full_cookies:
            messagebox.showinfo("提示", "Cookie池已经是空的")
            return

        # 确认清空
        if messagebox.askyesno("确认", f"确定要清空全部{len(self.full_cookies)}个Cookie吗?"):
            self.full_cookies.clear()
            self.cookie_listbox.delete(0, tk.END)
            messagebox.showinfo("成功", "Cookie池已清空,请记得保存配置")

    def _toggle_schedule(self):
        """启用/取消定时启动"""
        # 如果已经在等待,则取消
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self._cancel_schedule()
            return

        # 启用定时启动
        try:
            hour = int(self.hour_spinbox.get())
            minute = int(self.minute_spinbox.get())
            second = int(self.second_spinbox.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的时间")
            return

        # 构造目标时间
        target_time = datetime.now().replace(hour=hour, minute=minute, second=second, microsecond=0)
        now = datetime.now()

        # 检查时间是否已过
        if now >= target_time:
            messagebox.showerror("错误", f"时间已过!\n当前时间: {now.strftime('%H:%M:%S')}\n设置时间: {target_time.strftime('%H:%M:%S')}\n\n请设置今天未来的时间")
            return

        # 验证配置
        valid, error_msg = self.config_manager.validate()
        if not valid:
            messagebox.showerror("配置错误", f"定时启动前请先配置:\n{error_msg}")
            return

        # 重置停止事件
        self.schedule_stop_event.clear()

        # 更新UI状态
        self.schedule_btn.config(text="取消定时")
        self.hour_spinbox.config(state=tk.DISABLED)
        self.minute_spinbox.config(state=tk.DISABLED)
        self.second_spinbox.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)

        # 计算剩余时间
        remaining_seconds = (target_time - now).total_seconds()
        self._update_schedule_status(f"将在 {target_time.strftime('%H:%M:%S')} 启动 (剩余 {int(remaining_seconds)}秒)")

        # 启动定时器线程
        self.scheduler_thread = threading.Thread(
            target=self._wait_and_start,
            args=(target_time,),
            daemon=True
        )
        self.scheduler_thread.start()

        # 启动倒计时更新
        self._update_countdown(target_time)

    def _cancel_schedule(self):
        """取消定时启动"""
        self.schedule_stop_event.set()
        self.schedule_btn.config(text="启用定时")
        self.hour_spinbox.config(state=tk.NORMAL)
        self.minute_spinbox.config(state=tk.NORMAL)
        self.second_spinbox.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.NORMAL)
        self._update_schedule_status("定时已取消")

    def _wait_and_start(self, target_time):
        """等待到达目标时间后启动执行(后台线程)"""
        try:
            while datetime.now() < target_time:
                # 检查是否被取消
                if self.schedule_stop_event.is_set():
                    return

                # 每500ms检查一次
                time.sleep(0.5)

            # 到达目标时间,触发启动
            if not self.schedule_stop_event.is_set():
                self.root.after(0, self._scheduled_start)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("定时启动错误", f"定时器异常: {e}"))

    def _scheduled_start(self):
        """定时启动触发点"""
        self._update_schedule_status("时间到! 正在启动...")

        # 重置UI状态
        self.schedule_btn.config(text="启用定时")
        self.hour_spinbox.config(state=tk.NORMAL)
        self.minute_spinbox.config(state=tk.NORMAL)
        self.second_spinbox.config(state=tk.NORMAL)

        # 执行启动
        self._start_execution()

    def _update_countdown(self, target_time):
        """更新倒计时显示"""
        if not self.scheduler_thread or not self.scheduler_thread.is_alive():
            return

        now = datetime.now()
        if now >= target_time:
            return

        remaining_seconds = int((target_time - now).total_seconds())
        self._update_schedule_status(f"将在 {target_time.strftime('%H:%M:%S')} 启动 (剩余 {remaining_seconds}秒)")

        # 每秒更新一次
        self.root.after(1000, lambda: self._update_countdown(target_time))

    def _update_schedule_status(self, text: str):
        """更新定时状态标签"""
        self.schedule_status_label.config(text=text)

    def _toggle_auto_keyword(self):
        """切换自动计算关键词模式"""
        if self.auto_keyword_var.get():
            # 启用自动计算 - 禁用所有输入控件防止误修改
            self.keyword_entry.config(state=tk.DISABLED)
            self.keyword_prefix_entry.config(state=tk.DISABLED)
            self.start_year_spinbox.config(state=tk.DISABLED)
            self.start_month_spinbox.config(state=tk.DISABLED)
            self.start_day_spinbox.config(state=tk.DISABLED)
            self._update_auto_keyword()
        else:
            # 禁用自动计算 - 启用手动输入
            self.keyword_entry.config(state=tk.NORMAL)
            self.keyword_prefix_entry.config(state=tk.DISABLED)
            self.start_year_spinbox.config(state=tk.DISABLED)
            self.start_month_spinbox.config(state=tk.DISABLED)
            self.start_day_spinbox.config(state=tk.DISABLED)
            self.keyword_calc_label.config(text="")

    def _update_auto_keyword(self):
        """更新自动计算的关键词"""
        try:
            # 获取活动开始日期
            year = int(self.start_year_spinbox.get())
            month = int(self.start_month_spinbox.get())
            day = int(self.start_day_spinbox.get())
            start_date = datetime(year, month, day).date()

            # 计算今天是第几天
            today = datetime.now().date()
            day_number = (today - start_date).days + 1

            # 获取前缀
            prefix = self.keyword_prefix_entry.get().strip()
            if not prefix:
                prefix = "Day"

            # 生成关键词
            if day_number < 1:
                keyword = f"{prefix}1"
                self.keyword_calc_label.config(
                    text=f"⚠ 活动未开始 (将于 {start_date} 开始) → 使用 {keyword}",
                    foreground="orange"
                )
            else:
                keyword = f"{prefix}{day_number}"
                self.keyword_calc_label.config(
                    text=f"✓ 今天是第 {day_number} 天 → 关键词: {keyword}",
                    foreground="green"
                )

            # 更新到输入框(仅用于保存,但禁用状态下不可见)
            self.keyword_entry.config(state=tk.NORMAL)
            self.keyword_entry.delete(0, tk.END)
            self.keyword_entry.insert(0, keyword)
            self.keyword_entry.config(state=tk.DISABLED)

        except ValueError as e:
            self.keyword_calc_label.config(text=f"✗ 日期无效: {e}", foreground="red")

    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    app = RockKingdomGUI()
    app.run()


if __name__ == "__main__":
    main()
