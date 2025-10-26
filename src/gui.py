"""
GUI界面
使用Tkinter实现的配置和执行界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import io
from PIL import Image, ImageTk
from src.config_manager import ConfigManager
from src.redeemer import RedeemController
from src.logger import LoggerManager


class RockKingdomGUI:
    """洛克王国自动激活GUI界面"""

    def __init__(self):
        """初始化GUI"""
        self.root = tk.Tk()
        self.root.title("洛克王国自动激活工具")
        self.root.geometry("700x650")
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

        # Cookie池存储(完整Cookie字符串)
        self.full_cookies = []

        # 创建界面
        self._create_widgets()
        self._load_config_to_ui()

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
        watermark_label.grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)

        # 小程序Authorization
        ttk.Label(parent, text="小程序Authorization:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.miniapp_auth_entry = ttk.Entry(parent, width=60)
        self.miniapp_auth_entry.grid(row=1, column=1, padx=10, pady=5)

        # Cookie池管理
        ttk.Label(parent, text="网页端Cookie池:").grid(row=2, column=0, sticky=tk.NW, padx=10, pady=5)

        # Cookie池容器
        cookie_frame = ttk.Frame(parent)
        cookie_frame.grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)

        # Cookie列表框(带滚动条)
        list_frame = ttk.Frame(cookie_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.cookie_listbox = tk.Listbox(list_frame, width=70, height=6, yscrollcommand=scrollbar.set)
        self.cookie_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.cookie_listbox.yview)

        # Cookie操作按钮
        cookie_btn_frame = ttk.Frame(cookie_frame)
        cookie_btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(cookie_btn_frame, text="添加Cookie", command=self._add_cookie).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cookie_btn_frame, text="删除选中", command=self._remove_cookie).pack(side=tk.LEFT, padx=5)
        ttk.Button(cookie_btn_frame, text="清空全部", command=self._clear_cookies).pack(side=tk.LEFT, padx=5)

        ttk.Label(parent, text="(每个Cookie一个账号,程序会并发兑换)", font=("", 8), foreground="gray").grid(
            row=3, column=1, sticky=tk.W, padx=10
        )

        # 公告关键字
        ttk.Label(parent, text="公告关键字:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        self.keyword_entry = ttk.Entry(parent, width=60)
        self.keyword_entry.grid(row=4, column=1, padx=10, pady=5)
        ttk.Label(parent, text="(例如: Day1, Day2...)", font=("", 8), foreground="gray").grid(
            row=5, column=1, sticky=tk.W, padx=10
        )

        # 验证码选项
        ttk.Label(parent, text="验证码识别方式:").grid(row=6, column=0, sticky=tk.W, padx=10, pady=5)
        self.ocr_var = tk.BooleanVar()
        ocr_frame = ttk.Frame(parent)
        ocr_frame.grid(row=6, column=1, sticky=tk.W, padx=10, pady=5)
        ttk.Radiobutton(ocr_frame, text="手动输入", variable=self.ocr_var, value=False).pack(side=tk.LEFT)
        ttk.Radiobutton(ocr_frame, text="OCR自动识别", variable=self.ocr_var, value=True).pack(side=tk.LEFT, padx=20)

        # OCR重试次数
        ttk.Label(parent, text="OCR失败重试次数:").grid(row=7, column=0, sticky=tk.W, padx=10, pady=5)
        self.ocr_retries_spinbox = ttk.Spinbox(parent, from_=1, to=10, width=10)
        self.ocr_retries_spinbox.grid(row=7, column=1, sticky=tk.W, padx=10, pady=5)
        self.ocr_retries_spinbox.set(3)

        # 兑换重试次数
        ttk.Label(parent, text="兑换重试次数:").grid(row=8, column=0, sticky=tk.W, padx=10, pady=5)
        self.redeem_retries_spinbox = ttk.Spinbox(parent, from_=1, to=20, width=10)
        self.redeem_retries_spinbox.grid(row=8, column=1, sticky=tk.W, padx=10, pady=5)
        self.redeem_retries_spinbox.set(5)
        ttk.Label(parent, text="(验证码错误时自动重试)", font=("", 8), foreground="gray").grid(
            row=9, column=1, sticky=tk.W, padx=10
        )

        # 请求线程数
        ttk.Label(parent, text="请求线程数:").grid(row=10, column=0, sticky=tk.W, padx=10, pady=5)
        self.threads_spinbox = ttk.Spinbox(parent, from_=1, to=50, width=10)
        self.threads_spinbox.grid(row=10, column=1, sticky=tk.W, padx=10, pady=5)
        self.threads_spinbox.set(10)

        # 请求超时时间
        ttk.Label(parent, text="请求超时(秒):").grid(row=11, column=0, sticky=tk.W, padx=10, pady=5)
        self.timeout_spinbox = ttk.Spinbox(parent, from_=1, to=30, width=10)
        self.timeout_spinbox.grid(row=11, column=1, sticky=tk.W, padx=10, pady=5)
        self.timeout_spinbox.set(5)

        # 轮询间隔时间
        ttk.Label(parent, text="轮询间隔(秒):").grid(row=12, column=0, sticky=tk.W, padx=10, pady=5)
        self.poll_interval_spinbox = ttk.Spinbox(parent, from_=0.1, to=30.0, increment=0.1, width=10)
        self.poll_interval_spinbox.grid(row=12, column=1, sticky=tk.W, padx=10, pady=5)
        self.poll_interval_spinbox.set(1.0)
        ttk.Label(parent, text="(支持0.1秒精度,如0.5, 1.0等)", font=("", 8), foreground="gray").grid(
            row=13, column=1, sticky=tk.W, padx=10
        )

        # 代理配置
        ttk.Label(parent, text="代理设置:").grid(row=14, column=0, sticky=tk.W, padx=10, pady=5)
        proxy_frame = ttk.Frame(parent)
        proxy_frame.grid(row=14, column=1, sticky=tk.W, padx=10, pady=5)

        # 代理开关
        self.use_proxy_var = tk.BooleanVar()
        proxy_check = ttk.Checkbutton(proxy_frame, text="使用代理", variable=self.use_proxy_var,
                                       command=self._toggle_proxy_inputs)
        proxy_check.pack(side=tk.LEFT)

        # 代理主机
        ttk.Label(proxy_frame, text="主机:").pack(side=tk.LEFT, padx=(20, 5))
        self.proxy_host_entry = ttk.Entry(proxy_frame, width=20)
        self.proxy_host_entry.pack(side=tk.LEFT, padx=5)

        # 代理端口
        ttk.Label(proxy_frame, text="端口:").pack(side=tk.LEFT, padx=(10, 5))
        self.proxy_port_spinbox = ttk.Spinbox(proxy_frame, from_=1, to=65535, width=10)
        self.proxy_port_spinbox.pack(side=tk.LEFT, padx=5)

        ttk.Label(parent, text="(仅用于网页端请求:验证码、兑换)", font=("", 8), foreground="gray").grid(
            row=15, column=1, sticky=tk.W, padx=10
        )

        # 保存按钮
        save_btn = ttk.Button(parent, text="保存配置", command=self._save_config)
        save_btn.grid(row=16, column=1, sticky=tk.E, padx=10, pady=20)

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
        watermark_label.pack(fill=tk.X, padx=10, pady=10)

        # 状态显示
        ttk.Label(parent, text="执行状态:").pack(anchor=tk.W, padx=10, pady=5)
        self.status_label = ttk.Label(parent, text="就绪", foreground="green", font=("", 10, "bold"))
        self.status_label.pack(anchor=tk.W, padx=10)

        # 日志显示
        ttk.Label(parent, text="执行日志:").pack(anchor=tk.W, padx=10, pady=(10, 5))
        self.log_text = scrolledtext.ScrolledText(parent, width=80, height=20, state=tk.DISABLED)
        self.log_text.pack(padx=10, pady=5)

        # 按钮区域
        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=10)

        self.start_btn = ttk.Button(button_frame, text="开始执行", command=self._start_execution)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="暂停执行", command=self._stop_execution, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(button_frame, text="清空日志", command=self._clear_log)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

    def _load_config_to_ui(self):
        """加载配置到界面"""
        self.miniapp_auth_entry.insert(0, self.config_manager.get("miniapp_authorization", ""))

        # 加载Cookie列表
        self.full_cookies = self.config_manager.get("web_cookies", [])
        self.cookie_listbox.delete(0, tk.END)
        for cookie in self.full_cookies:
            # 截取Cookie前60个字符用于显示
            display_text = cookie[:60] + "..." if len(cookie) > 60 else cookie
            self.cookie_listbox.insert(tk.END, display_text)

        self.keyword_entry.insert(0, self.config_manager.get("announcement_keyword", "Day1"))
        self.ocr_var.set(self.config_manager.get("use_ocr", False))
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
            self.config_manager.set("miniapp_authorization", self.miniapp_auth_entry.get())
            self.config_manager.set("web_cookies", self.full_cookies)  # 保存完整Cookie列表
            self.config_manager.set("announcement_keyword", self.keyword_entry.get())
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
        """添加Cookie到Cookie池"""
        # 创建输入窗口
        dialog = tk.Toplevel(self.root)
        dialog.title("添加Cookie")
        dialog.geometry("500x200")
        dialog.resizable(False, False)
        dialog.grab_set()

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

    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    app = RockKingdomGUI()
    app.run()


if __name__ == "__main__":
    main()
