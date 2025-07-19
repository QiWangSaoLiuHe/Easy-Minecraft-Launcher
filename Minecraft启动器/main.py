import os
import json
import platform
import subprocess
import requests
import threading
import zipfile
import shutil
import traceback
import time
import hashlib
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, simpledialog, filedialog
from tkinter.font import Font
from tqdm import tqdm
from urllib.parse import urlparse
from PIL import Image, ImageTk
import webbrowser


class MinecraftBlueLauncher:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.load_assets()
        self.init_paths()
        self.load_config()

        # 初始化动画相关属性
        self.animations_running = True
        self.bg_color_index = 0
        self.bg_colors = ["#e6f7ff", "#d9f2ff", "#ccebff", "#bfe4ff"]
        self.wave_text = "~ ~ ~ ~ ~ ~ ~"

        self.setup_ui()
        self.refresh_local_versions()
        self.running_process = None
        self.start_background_animation()
        self.setup_system_encoding()

    def setup_window(self):
        """配置主窗口属性"""
        self.root.title("Easy Minecraft Launcher 1.0")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        self.root.configure(bg="#e6f7ff")  # 天蓝色背景

        # 设置窗口图标
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass

    def setup_system_encoding(self):
        """配置系统编码"""
        os.environ["PYTHONUTF8"] = "1"
        os.environ["PYTHONIOENCODING"] = "utf-8"

        if platform.system() == "Windows":
            try:
                import ctypes
                ctypes.windll.kernel32.SetConsoleOutputCP(65001)
                ctypes.windll.kernel32.SetConsoleCP(65001)
            except:
                self.log("无法设置控制台编码", "warning")

    def load_assets(self):
        """加载资源文件"""
        self.icons = {}
        self.images = {}

        # 加载背景图片（示例）
        try:
            bg_image = Image.open("background.png").resize((1000, 700))
            self.images["background"] = ImageTk.PhotoImage(bg_image)
        except:
            pass

    def start_background_animation(self):
        """启动背景动画效果"""
        self.bg_color_index = 0
        self.bg_colors = ["#e6f7ff", "#d9f2ff", "#ccebff", "#bfe4ff"]
        self.animate_background()

    def animate_background(self):
        """背景颜色渐变动画"""
        if not self.animations_running:
            return

        current_color = self.bg_colors[self.bg_color_index % len(self.bg_colors)]
        self.root.configure(bg=current_color)

        # 更新所有子部件的背景色
        for child in self.root.winfo_children():
            try:
                child.configure(bg=current_color)
            except:
                pass

        self.bg_color_index += 1
        self.root.after(3000, self.animate_background)

    def configure_styles(self):
        """配置UI样式"""
        self.style = ttk.Style()

        # 天蓝色主题
        self.style.theme_create("skyblue", parent="clam", settings={
            "TFrame": {
                "configure": {"background": "#e6f7ff"}
            },
            "TLabel": {
                "configure": {
                    "background": "#e6f7ff",
                    "foreground": "#0066cc",
                    "font": ("微软雅黑", 10)
                }
            },
            "TButton": {
                "configure": {
                    "background": "#4da6ff",
                    "foreground": "white",
                    "borderwidth": 1,
                    "focusthickness": 3,
                    "focuscolor": "none",
                    "font": ("微软雅黑", 10),
                    "padding": 5
                },
                "map": {
                    "background": [("active", "#66b3ff")]
                }
            },
            "TEntry": {
                "configure": {
                    "fieldbackground": "white",
                    "foreground": "#0066cc",
                    "insertcolor": "#0066cc",
                    "borderwidth": 1,
                    "font": ("微软雅黑", 10)
                }
            },
            "TCombobox": {
                "configure": {
                    "fieldbackground": "white",
                    "foreground": "#0066cc",
                    "font": ("微软雅黑", 10)
                }
            },
            "TScrollbar": {
                "configure": {
                    "background": "#4da6ff",
                    "troughcolor": "#ccebff"
                }
            },
            "TLabelFrame": {
                "configure": {
                    "background": "#e6f7ff",
                    "foreground": "#0066cc",
                    "font": ("微软雅黑", 10, "bold")
                }
            },
            "Vertical.TScrollbar": {
                "configure": {
                    "background": "#4da6ff"
                }
            }
        })
        self.style.theme_use("skyblue")

        # 自定义标签样式
        self.style.configure("Title.TLabel",
                             font=("微软雅黑", 16, "bold"),
                             foreground="#004080")

        self.style.configure("Status.TLabel",
                             font=("微软雅黑", 9),
                             foreground="#004080")

        # 按钮动画效果
        self.style.map("TButton",
                       background=[("active", "#66b3ff"), ("pressed", "#3385ff")])

    def init_paths(self):
        """初始化路径系统"""
        system = platform.system()
        if system == "Windows":
            self.minecraft_dir = os.path.join(os.getenv('APPDATA'), '.minecraft')
        elif system == "Darwin":
            self.minecraft_dir = os.path.expanduser('~/Library/Application Support/minecraft')
        else:
            self.minecraft_dir = os.path.expanduser('~/.minecraft')

        # 创建必要目录
        required_dirs = [
            'versions',
            'libraries',
            'assets',
            'assets/indexes',
            'assets/objects',
            'logs',
            'crash-reports',
            'mods'  # 新增mods目录
        ]

        for dir_name in required_dirs:
            os.makedirs(os.path.join(self.minecraft_dir, dir_name), exist_ok=True)

        # 配置文件路径
        self.config_path = os.path.join(self.minecraft_dir, 'launcher_config.json')
        self.log_file = os.path.join(self.minecraft_dir, 'launcher.log')

    def load_config(self):
        """加载配置文件"""
        default_config = {
            'username': 'Player',
            'memory': '2048',
            'java_path': self.detect_java(),
            'mirror': 'BMCLAPI',
            'game_dir': self.minecraft_dir,
            'window_width': 1000,
            'window_height': 700,
            'last_version': '',
            'fabric_version': '',  # 新增Fabric版本配置
            'forge_version': ''  # 新增Forge版本配置
        }

        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = {**default_config, **json.load(f)}
            else:
                self.config = default_config
        except Exception as e:
            self.log(f"加载配置失败: {e}", "error")
            self.config = default_config

        # 应用窗口尺寸
        self.root.geometry(f"{self.config['window_width']}x{self.config['window_height']}")

    def save_config(self):
        """保存配置文件"""
        try:
            # 保存窗口尺寸
            self.config['window_width'] = self.root.winfo_width()
            self.config['window_height'] = self.root.winfo_height()

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"保存配置失败: {e}", "error")

    def detect_java(self):
        """自动检测Java路径"""
        try:
            # 尝试通过which/where命令查找
            java_path = subprocess.check_output(
                ['where' if platform.system() == 'Windows' else 'which', 'java'],
                stderr=subprocess.DEVNULL
            ).decode('utf-8', errors='ignore').strip()
            if java_path and os.path.exists(java_path):
                return java_path
        except:
            pass

        # 常见Java安装路径
        common_paths = [
            '/usr/bin/java',
            '/usr/local/bin/java',
            'C:\\Program Files\\Java\\jre\\bin\\java.exe',
            'C:\\Program Files\\Java\\jdk\\bin\\java.exe',
            'C:\\Program Files (x86)\\Java\\jre\\bin\\java.exe'
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return 'java'  # 最后尝试PATH中的java

    def setup_ui(self):
        """构建用户界面"""
        self.configure_styles()

        # 主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 顶部横幅
        self.create_banner(main_container)

        # 主内容区
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=BOTH, expand=True)

        # 左侧面板 - 版本列表
        self.create_version_panel(content_frame)

        # 右侧面板 - 设置和操作
        self.create_settings_panel(content_frame)

        # 底部状态栏
        self.create_status_bar(main_container)

        # 悬浮动画效果
        self.setup_hover_effects()

    def setup_hover_effects(self):
        """设置按钮悬浮动画"""

        def on_enter(e):
            e.widget.configure(style="Hover.TButton")
            if hasattr(e.widget, 'original_bg'):
                e.widget.configure(background=e.widget.original_bg)

        def on_leave(e):
            e.widget.configure(style="TButton")

        # 为所有按钮添加悬浮效果
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Button):
                child.bind("<Enter>", on_enter)
                child.bind("<Leave>", on_leave)

        # 创建悬浮样式
        self.style.configure("Hover.TButton",
                             background="#80bfff",
                             foreground="white")

    def create_banner(self, parent):
        """创建顶部横幅"""
        banner_frame = ttk.Frame(parent)
        banner_frame.pack(fill=X, pady=(0, 10))

        # 标题
        title_label = ttk.Label(
            banner_frame,
            text="MINECRAFT 离线启动器",
            style="Title.TLabel"
        )
        title_label.pack(side=LEFT)

        # 添加波浪动画效果
        self.wave_text = "~ ~ ~ ~ ~ ~ ~"
        self.wave_label = ttk.Label(
            banner_frame,
            text=self.wave_text,
            font=("微软雅黑", 12),
            foreground="#66b3ff"
        )
        self.wave_label.pack(side=LEFT, padx=10)
        self.animate_wave()

        # 帮助按钮
        help_btn = ttk.Button(
            banner_frame,
            text="帮助",
            command=lambda: webbrowser.open("https://minecraft.fandom.com/wiki/Help:Installing"),
            style="Accent.TButton"
        )
        help_btn.pack(side=RIGHT, padx=5)

    def animate_wave(self):
        """标题波浪动画"""
        if not self.animations_running:
            return

        self.wave_text = self.wave_text[1:] + self.wave_text[0]
        self.wave_label.config(text=self.wave_text)
        self.root.after(300, self.animate_wave)

    def create_version_panel(self, parent):
        """创建版本列表面板"""
        left_panel = ttk.LabelFrame(parent, text=" 游戏版本 ", padding=10)
        left_panel.pack(side=LEFT, fill=Y, padx=(0, 10))

        # 搜索框
        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill=X, pady=(0, 5))

        self.search_var = StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=LEFT, fill=X, expand=True)
        search_entry.bind('<KeyRelease>', self.filter_versions)

        search_btn = ttk.Button(
            search_frame,
            text="🔍",
            width=3,
            command=self.filter_versions,
            style="Accent.TButton"
        )
        search_btn.pack(side=LEFT, padx=(5, 0))

        # 版本列表框
        version_frame = ttk.Frame(left_panel)
        version_frame.pack(fill=BOTH, expand=True)

        self.version_listbox = Listbox(
            version_frame,
            bg="white",
            fg="#0066cc",
            selectbackground="#4da6ff",
            selectforeground="white",
            borderwidth=1,
            highlightthickness=0,
            font=('Consolas', 10),
            relief="solid"
        )
        self.version_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            version_frame,
            orient=VERTICAL,
            command=self.version_listbox.yview
        )
        scrollbar.pack(side=RIGHT, fill=Y)
        self.version_listbox.config(yscrollcommand=scrollbar.set)

        # 版本操作按钮
        button_frame = ttk.Frame(left_panel)
        button_frame.pack(fill=X, pady=(5, 0))

        delete_btn = ttk.Button(
            button_frame,
            text="删除版本",
            command=self.delete_version,
            style="Accent.TButton"
        )
        delete_btn.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        open_btn = ttk.Button(
            button_frame,
            text="打开目录",
            command=self.open_versions_dir,
            style="Accent.TButton"
        )
        open_btn.pack(side=LEFT, fill=X, expand=True)

        # 新增Fabric/Forge安装按钮
        mod_button_frame = ttk.Frame(left_panel)
        mod_button_frame.pack(fill=X, pady=(5, 0))

        fabric_btn = ttk.Button(
            mod_button_frame,
            text="安装Fabric",
            command=self.install_fabric,
            style="Accent.TButton"
        )
        fabric_btn.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        forge_btn = ttk.Button(
            mod_button_frame,
            text="安装Forge",
            command=self.install_forge,
            style="Accent.TButton"
        )
        forge_btn.pack(side=LEFT, fill=X, expand=True)

    def create_settings_panel(self, parent):
        """创建设置面板"""
        right_panel = ttk.Frame(parent)
        right_panel.pack(side=RIGHT, fill=BOTH, expand=True)

        # 账号设置
        self.create_account_settings(right_panel)

        # Java设置
        self.create_java_settings(right_panel)

        # 下载设置
        self.create_download_settings(right_panel)

        # 主操作按钮
        self.create_action_buttons(right_panel)

        # 日志区域
        self.create_log_panel(right_panel)

    def create_account_settings(self, parent):
        """创建账号设置区域"""
        account_frame = ttk.LabelFrame(parent, text=" 账号设置 ", padding=10)
        account_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(account_frame, text="玩家名称:").grid(row=0, column=0, sticky=W, pady=2)
        self.username_entry = ttk.Entry(account_frame)
        self.username_entry.grid(row=0, column=1, sticky=EW, pady=2)
        self.username_entry.insert(0, self.config['username'])

    def create_java_settings(self, parent):
        """创建Java设置区域"""
        java_frame = ttk.LabelFrame(parent, text=" Java设置 ", padding=10)
        java_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(java_frame, text="Java路径:").grid(row=0, column=0, sticky=W, pady=2)

        self.java_entry = ttk.Entry(java_frame)
        self.java_entry.grid(row=0, column=1, sticky=EW, pady=2)
        self.java_entry.insert(0, self.config['java_path'])

        browse_btn = ttk.Button(
            java_frame,
            text="浏览...",
            command=self.browse_java,
            style="Accent.TButton"
        )
        browse_btn.grid(row=0, column=2, padx=(5, 0))

        ttk.Label(java_frame, text="内存(MB):").grid(row=1, column=0, sticky=W, pady=2)
        self.memory_entry = ttk.Entry(java_frame)
        self.memory_entry.grid(row=1, column=1, sticky=EW, pady=2)
        self.memory_entry.insert(0, self.config['memory'])

        # Java验证标签
        self.java_status_label = ttk.Label(
            java_frame,
            text="",
            style="Status.TLabel"
        )
        self.java_status_label.grid(row=2, column=0, columnspan=3, sticky=W)

        # 初始验证Java
        self.verify_java()

    def create_download_settings(self, parent):
        """创建下载设置区域"""
        download_frame = ttk.LabelFrame(parent, text=" 下载设置 ", padding=10)
        download_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(download_frame, text="镜像源:").grid(row=0, column=0, sticky=W, pady=2)
        self.mirror_combobox = ttk.Combobox(
            download_frame,
            values=["BMCLAPI", "MCBBS", "官方源"],
            state="readonly"
        )
        self.mirror_combobox.grid(row=0, column=1, sticky=EW, pady=2)
        self.mirror_combobox.set(self.config['mirror'])

        ttk.Label(download_frame, text="版本号:").grid(row=1, column=0, sticky=W, pady=2)

        version_frame = ttk.Frame(download_frame)
        version_frame.grid(row=1, column=1, sticky=EW)

        self.version_entry = ttk.Entry(version_frame)
        self.version_entry.pack(side=LEFT, fill=X, expand=True)

        ttk.Button(
            version_frame,
            text="获取版本",
            command=self.fetch_versions_list,
            width=10,
            style="Accent.TButton"
        ).pack(side=LEFT, padx=(5, 0))

    def create_action_buttons(self, parent):
        """创建操作按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=X, pady=(10, 0))

        self.download_btn = ttk.Button(
            button_frame,
            text="下载版本",
            command=self.download_version,
            style="Accent.TButton"
        )
        self.download_btn.pack(side=LEFT, padx=(0, 5), fill=X, expand=True)

        self.launch_btn = ttk.Button(
            button_frame,
            text="启动游戏",
            command=self.launch_game,
            style="Accent.TButton"
        )
        self.launch_btn.pack(side=LEFT, padx=(0, 5), fill=X, expand=True)

        self.refresh_btn = ttk.Button(
            button_frame,
            text="刷新列表",
            command=self.refresh_local_versions,
            style="Accent.TButton"
        )
        self.refresh_btn.pack(side=LEFT, fill=X, expand=True)

    def create_log_panel(self, parent):
        """创建日志面板"""
        log_frame = ttk.LabelFrame(parent, text=" 日志 ", padding=10)
        log_frame.pack(fill=BOTH, expand=True)

        self.log_text = Text(
            log_frame,
            wrap=WORD,
            bg="white",
            fg="#0066cc",
            insertbackground="#0066cc",
            borderwidth=1,
            highlightthickness=0,
            font=('Consolas', 9),
            relief="solid"
        )
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient=VERTICAL,
            command=self.log_text.yview
        )
        scrollbar.pack(side=RIGHT, fill=Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 配置标签样式
        self.log_text.tag_config("info", foreground="#0066cc")
        self.log_text.tag_config("success", foreground="#009933")
        self.log_text.tag_config("error", foreground="#ff3333")
        self.log_text.tag_config("warning", foreground="#ff9900")

    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent, relief=SUNKEN)
        status_frame.pack(fill=X, pady=(10, 0))

        self.status_label = ttk.Label(
            status_frame,
            text="就绪",
            style="Status.TLabel"
        )
        self.status_label.pack(side=LEFT, padx=5)

        # 添加内存使用显示
        self.memory_usage_label = ttk.Label(
            status_frame,
            text="",
            style="Status.TLabel"
        )
        self.memory_usage_label.pack(side=RIGHT, padx=5)

        # 更新内存使用信息
        self.update_memory_usage()

    def update_memory_usage(self):
        """更新内存使用信息"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            self.memory_usage_label.config(
                text=f"内存: {mem.used // 1024 // 1024}MB/{mem.total // 1024 // 1024}MB ({mem.percent}%)"
            )
        except ImportError:
            self.memory_usage_label.config(text="安装psutil可查看内存使用")

        self.root.after(5000, self.update_memory_usage)

    def verify_java(self):
        """验证Java安装"""
        java_path = self.java_entry.get().strip()
        if not java_path:
            self.java_status_label.config(text="未设置Java路径", style="Error.TLabel")
            return False

        try:
            # 检查Java版本
            result = subprocess.run(
                [java_path, "-version"],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )

            output = result.stderr or result.stdout
            if "version" not in output.lower():
                raise ValueError("无效的Java输出")

            self.java_status_label.config(text="Java验证通过", style="Status.TLabel")
            return True
        except Exception as e:
            self.java_status_label.config(
                text=f"Java验证失败: {str(e)}",
                style="Error.TLabel"
            )
            return False

    def browse_java(self):
        """浏览Java路径"""
        initial_dir = os.path.dirname(self.java_entry.get()) or "C:\\Program Files\\Java"
        filepath = filedialog.askopenfilename(
            title="选择Java可执行文件",
            initialdir=initial_dir,
            filetypes=[("Java Executable", "java.exe javaw.exe java")]
        )
        if filepath:
            self.java_entry.delete(0, END)
            self.java_entry.insert(0, filepath)
            self.verify_java()

    def open_versions_dir(self):
        """打开版本目录"""
        versions_dir = os.path.join(self.minecraft_dir, 'versions')
        os.makedirs(versions_dir, exist_ok=True)

        if platform.system() == "Windows":
            os.startfile(versions_dir)
        elif platform.system() == "Darwin":
            subprocess.run(["open", versions_dir])
        else:
            subprocess.run(["xdg-open", versions_dir])

    def filter_versions(self, event=None):
        """过滤版本列表"""
        search_term = self.search_var.get().lower()
        self.version_listbox.delete(0, END)

        versions_dir = os.path.join(self.minecraft_dir, 'versions')
        if not os.path.exists(versions_dir):
            return

        versions = []
        for version in os.listdir(versions_dir):
            version_dir = os.path.join(versions_dir, version)
            if os.path.isdir(version_dir):
                json_path = os.path.join(version_dir, f"{version}.json")
                jar_path = os.path.join(version_dir, f"{version}.jar")
                if os.path.exists(json_path) and os.path.exists(jar_path):
                    if search_term in version.lower():
                        versions.append(version)

        versions.sort(reverse=True)
        for version in versions:
            self.version_listbox.insert(END, version)

    def refresh_local_versions(self):
        """刷新本地版本列表"""
        self.search_var.set("")
        self.filter_versions()
        self.log("本地版本列表已刷新")

    def fetch_versions_list(self):
        """获取可下载版本列表"""
        mirror_url = self.get_mirror_url()
        manifest_url = f"{mirror_url}/mc/game/version_manifest.json"

        try:
            self.log(f"获取版本列表从: {manifest_url}")
            response = requests.get(manifest_url, timeout=10)
            response.raise_for_status()

            manifest = response.json()
            versions = [v['id'] for v in manifest['versions']]

            # 显示版本选择对话框
            self.show_version_selection(versions)
        except Exception as e:
            self.log(f"获取版本列表失败: {str(e)}", "error")
            messagebox.showerror("错误", f"获取版本列表失败:\n{str(e)}")

    def show_version_selection(self, versions):
        """显示版本选择对话框"""
        selection_dialog = Toplevel(self.root)
        selection_dialog.title("选择Minecraft版本")
        selection_dialog.transient(self.root)
        selection_dialog.grab_set()

        # 居中对话框
        window_width = 400
        window_height = 500
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        selection_dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 搜索框
        search_frame = ttk.Frame(selection_dialog)
        search_frame.pack(fill=X, padx=10, pady=10)

        search_var = StringVar()
        ttk.Entry(search_frame, textvariable=search_var).pack(side=LEFT, fill=X, expand=True)

        # 版本列表
        list_frame = ttk.Frame(selection_dialog)
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        listbox = Listbox(
            list_frame,
            bg="white",
            fg="#0066cc",
            selectbackground="#4da6ff",
            selectforeground="white",
            borderwidth=1,
            highlightthickness=0,
            font=('Consolas', 10),
            relief="solid"
        )
        listbox.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=listbox.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        listbox.config(yscrollcommand=scrollbar.set)

        # 填充版本列表
        for version in sorted(versions, reverse=True):
            listbox.insert(END, version)

        # 搜索功能
        def update_list(event=None):
            search_term = search_var.get().lower()
            listbox.delete(0, END)
            for version in versions:
                if search_term in version.lower():
                    listbox.insert(END, version)

        search_var.trace("w", lambda *args: update_list())

        # 选择按钮
        def on_select():
            selection = listbox.curselection()
            if selection:
                self.version_entry.delete(0, END)
                self.version_entry.insert(0, listbox.get(selection[0]))
                selection_dialog.destroy()

        button_frame = ttk.Frame(selection_dialog)
        button_frame.pack(fill=X, padx=10, pady=(0, 10))

        ttk.Button(
            button_frame,
            text="选择",
            command=on_select,
            style="Accent.TButton"
        ).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="取消",
            command=selection_dialog.destroy,
            style="Accent.TButton"
        ).pack(side=LEFT, fill=X, expand=True)

    def get_mirror_url(self):
        """获取当前镜像源URL"""
        mirror_name = self.mirror_combobox.get()
        return {
            "BMCLAPI": "https://bmclapi2.bangbang93.com",
            "MCBBS": "https://download.mcbbs.net",
            "官方源": "https://launchermeta.mojang.com"
        }.get(mirror_name, "https://launchermeta.mojang.com")

    def download_version(self):
        """下载游戏版本"""
        version = self.version_entry.get().strip()
        if not version:
            messagebox.showerror("错误", "请输入要下载的版本号")
            return

        if not self.verify_java():
            messagebox.showerror("错误", "请先验证Java路径是否正确")
            return

        mirror_url = self.get_mirror_url()

        # 在新线程中下载
        threading.Thread(
            target=self._download_version_thread,
            args=(version, mirror_url),
            daemon=True
        ).start()

    def _download_version_thread(self, version, mirror_url):
        """下载版本的线程"""
        try:
            self.set_status(f"正在下载 {version}...")
            self.log(f"开始下载版本 {version}，使用镜像源: {mirror_url}")

            # 禁用按钮防止重复操作
            self.toggle_buttons(False)

            # 1. 获取版本清单
            self.log("获取版本清单...")
            manifest_url = f"{mirror_url}/mc/game/version_manifest.json"
            manifest = self.http_get(manifest_url).json()

            # 2. 查找指定版本
            version_info = None
            for v in manifest['versions']:
                if v['id'] == version:
                    version_url = v['url'].replace(
                        "https://launchermeta.mojang.com",
                        mirror_url
                    )
                    self.log(f"获取版本信息: {version_url}")
                    version_info = self.http_get(version_url).json()
                    break

            if not version_info:
                self.log(f"错误: 找不到版本 {version}", "error")
                messagebox.showerror("错误", f"找不到版本 {version}")
                return

            # 3. 创建版本目录
            version_dir = os.path.join(self.minecraft_dir, 'versions', version)
            os.makedirs(version_dir, exist_ok=True)

            # 4. 保存版本json
            json_path = os.path.join(version_dir, f"{version}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, indent=2, ensure_ascii=False)
            self.log(f"版本信息已保存: {json_path}")

            # 5. 下载客户端JAR
            client_url = version_info['downloads']['client']['url']
            client_url = client_url.replace(
                "https://launcher.mojang.com",
                mirror_url
            )
            jar_path = os.path.join(version_dir, f"{version}.jar")
            self.log(f"下载客户端: {client_url}")
            self.download_file(client_url, jar_path)

            # 6. 下载资源索引
            assets_url = version_info['assetIndex']['url']
            assets_url = assets_url.replace(
                "https://launchermeta.mojang.com",
                mirror_url
            )
            assets_index_path = os.path.join(
                self.minecraft_dir,
                'assets',
                'indexes',
                f"{version_info['assets']}.json"
            )
            self.log(f"下载资源索引: {assets_url}")
            self.download_file(assets_url, assets_index_path)

            # 7. 下载依赖库
            self.log("开始下载依赖库...")
            libraries_dir = os.path.join(self.minecraft_dir, 'libraries')
            os.makedirs(libraries_dir, exist_ok=True)

            for lib in version_info['libraries']:
                if 'rules' in lib and not self.check_library_rules(lib['rules']):
                    continue

                # 确保下载主库文件
                if 'downloads' in lib and 'artifact' in lib['downloads']:
                    lib_url = lib['downloads']['artifact']['url'].replace(
                        "https://libraries.minecraft.net",
                        f"{mirror_url}/maven"
                    )
                    lib_path = os.path.join(
                        self.minecraft_dir,
                        'libraries',
                        lib['downloads']['artifact']['path']
                    )

                    if not os.path.exists(lib_path):
                        try:
                            self.download_file(lib_url, lib_path)
                        except Exception as e:
                            self.log(f"下载库失败: {lib_url} - {str(e)}", "error")
                            continue

            # 8. 下载原生库
            self.log("处理原生库...")
            natives_dir = os.path.join(version_dir, 'natives')
            if os.path.exists(natives_dir):
                shutil.rmtree(natives_dir)
            os.makedirs(natives_dir)

            for lib in version_info['libraries']:
                if 'natives' in lib:
                    platform_key = {
                        "windows": "natives-windows",
                        "darwin": "natives-macos",
                        "linux": "natives-linux"
                    }.get(platform.system().lower())

                    if platform_key and platform_key in lib['natives']:
                        classifier = lib['natives'][platform_key].replace("${arch}", platform.machine())
                        if 'classifiers' in lib['downloads'] and classifier in lib['downloads']['classifiers']:
                            native_url = lib['downloads']['classifiers'][classifier]['url']
                            native_url = native_url.replace(
                                "https://libraries.minecraft.net",
                                f"{mirror_url}/maven"
                            )
                            native_path = os.path.join(natives_dir, os.path.basename(native_url))
                            self.log(f"下载原生库: {native_url}")
                            try:
                                self.download_file(native_url, native_path)

                                # 解压原生库
                                with zipfile.ZipFile(native_path, 'r') as zip_ref:
                                    zip_ref.extractall(natives_dir)
                                os.remove(native_path)
                            except Exception as e:
                                self.log(f"下载原生库失败: {str(e)}", "error")

            self.log(f"版本 {version} 下载完成!", "success")
            messagebox.showinfo("成功", f"版本 {version} 下载完成!")
            self.refresh_local_versions()

        except Exception as e:
            error_msg = str(e)
            self.log(f"下载失败: {error_msg}", "error")
            self.log(traceback.format_exc(), "error")
            messagebox.showerror("错误", f"下载失败:\n{error_msg}")
        finally:
            self.set_status("就绪")
            self.toggle_buttons(True)

    def http_get(self, url, max_retries=3, timeout=30):
        """带重试的HTTP请求"""
        for i in range(max_retries):
            try:
                # 确保URL正确处理镜像源
                parsed = urlparse(url)
                if "launchermeta.mojang.com" in parsed.netloc:
                    mirror_url = self.get_mirror_url()
                    url = url.replace("https://launchermeta.mojang.com", mirror_url)
                elif "libraries.minecraft.net" in parsed.netloc:
                    mirror_url = self.get_mirror_url()
                    url = url.replace("https://libraries.minecraft.net", f"{mirror_url}/maven")

                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if i == max_retries - 1:
                    raise
                wait_time = (i + 1) * 2  # 指数退避
                time.sleep(wait_time)
                self.log(f"请求失败，重试 {i + 1}/{max_retries} (等待 {wait_time}秒): {str(e)}", "warning")

    def download_file(self, url, path):
        """下载文件并显示进度"""
        mirror_url = self.get_mirror_url()
        download_sources = [
            url,
            url.replace("https://launchermeta.mojang.com", mirror_url),
            url.replace("https://libraries.minecraft.net", f"{mirror_url}/maven"),
            url.replace("https://launcher.mojang.com", mirror_url)
        ]

        last_error = None
        for source in download_sources:
            try:
                response = requests.get(source, stream=True, timeout=60)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                os.makedirs(os.path.dirname(path), exist_ok=True)

                with open(path, 'wb') as f, tqdm(
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        desc=os.path.basename(path),
                        miniters=1
                ) as bar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
                return  # 下载成功则返回

            except Exception as e:
                last_error = e
                continue

        # 所有源都失败
        raise Exception(f"所有下载源尝试失败: {str(last_error)}")

    def check_library_rules(self, rules):
        """检查库规则是否适用当前系统"""
        if not rules:
            return True

        system_name = platform.system().lower()
        system_arch = platform.machine().lower()

        allow = False
        for rule in rules:
            if rule['action'] == 'allow':
                if 'os' in rule:
                    if rule['os']['name'] != system_name:
                        return False
                    allow = True
                else:
                    allow = True
            elif rule['action'] == 'disallow':
                if 'os' in rule:
                    if rule['os']['name'] == system_name:
                        return False

        return allow

    def launch_game(self):
        """启动游戏"""
        selection = self.version_listbox.curselection()
        if not selection:
            messagebox.showerror("错误", "请选择要启动的版本")
            return

        version = self.version_listbox.get(selection[0])
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("错误", "请输入用户名")
            return

        if not self.verify_java():
            messagebox.showerror("错误", "请先验证Java路径是否正确")
            return

        # 在新线程中启动游戏
        threading.Thread(
            target=self._launch_game_thread,
            args=(version, username),
            daemon=True
        ).start()

    def _launch_game_thread(self, version, username):
        """启动游戏的线程"""
        try:
            self.set_status(f"正在启动 {version}...")
            self.log(f"准备启动版本 {version}...")

            # 禁用按钮防止重复操作
            self.toggle_buttons(False)

            # 1. 加载版本信息
            version_dir = os.path.join(self.minecraft_dir, 'versions', version)
            json_path = os.path.join(version_dir, f"{version}.json")

            with open(json_path, 'r', encoding='utf-8') as f:
                version_data = json.load(f)

            # 2. 验证文件完整性
            missing_files = self.verify_game_files(version, version_data)
            if missing_files:
                self.log(f"缺失文件: {', '.join(missing_files)}", "error")
                if not messagebox.askyesno("错误", "游戏文件不完整，是否尝试修复？"):
                    return

                # 尝试重新下载缺失文件
                self.repair_game_files(version, version_data, missing_files)

            # 3. 构建classpath
            libraries = []
            libraries_dir = os.path.join(self.minecraft_dir, 'libraries')

            for lib in version_data['libraries']:
                if 'rules' in lib and not self.check_library_rules(lib['rules']):
                    continue

                # 主库文件
                if 'downloads' in lib and 'artifact' in lib['downloads']:
                    lib_path = os.path.join(
                        libraries_dir,
                        lib['downloads']['artifact']['path']
                    )
                    if os.path.exists(lib_path):
                        libraries.append(lib_path)

            # 添加主JAR
            main_jar = os.path.join(version_dir, f"{version}.jar")
            classpath = os.pathsep.join([main_jar] + libraries)

            # 4. 准备natives目录
            natives_dir = os.path.join(version_dir, 'natives')
            if not os.path.exists(natives_dir):
                os.makedirs(natives_dir)

            # 5. 构建启动命令
            java_path = self.java_entry.get().strip()
            memory = self.memory_entry.get().strip()

            try:
                memory_mb = int(memory)
                if memory_mb < 1024:
                    self.log("警告: 建议分配至少1024MB内存", "warning")
            except ValueError:
                memory_mb = 2048
                self.log("警告: 内存值无效，使用默认2048MB", "warning")

            # 检查是否是Fabric或Forge版本
            if "fabric" in version.lower():
                self.log("检测到Fabric版本，使用Fabric启动逻辑")
                cmd = self._build_fabric_command(java_path, memory_mb, version, version_data, natives_dir, username)
            elif "forge" in version.lower():
                self.log("检测到Forge版本，使用Forge启动逻辑")
                cmd = self._build_forge_command(java_path, memory_mb, version, version_data, natives_dir, username)
            else:
                # 普通版本
                cmd = [
                    java_path,
                    f"-Xmx{memory_mb}M",
                    f"-Xms{max(512, memory_mb // 2)}M",
                    f"-Djava.library.path={natives_dir}",
                    f"-Dminecraft.client.jar={main_jar}",
                    "-cp", classpath,
                    version_data['mainClass'],
                    "--username", username,
                    "--version", version,
                    "--gameDir", self.minecraft_dir,
                    "--assetsDir", os.path.join(self.minecraft_dir, 'assets'),
                    "--assetIndex", version_data['assets'],
                    "--accessToken", "0",
                    "--userType", "legacy",
                    "--versionType", "release",
                    "--width", "854",
                    "--height", "480"
                ]

                # 6. 添加日志配置
                cmd.extend([
                    "-Dlog4j.configurationFile=client-1.12.xml",
                    "-Dfml.ignoreInvalidMinecraftCertificates=true",
                    "-Dfml.ignorePatchDiscrepancies=true"
                ])

            # 7. 启动游戏
            self.log("启动命令: " + " ".join(cmd))
            self.log("游戏启动中...")

            # 创建日志文件
            game_log_file = os.path.join(self.minecraft_dir, "logs", "launcher_output.log")
            os.makedirs(os.path.dirname(game_log_file), exist_ok=True)

            with open(game_log_file, 'w', encoding='utf-8') as log_f:
                process = self.create_game_process(cmd)
                self.running_process = process

                # 实时输出日志
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = self.safe_decode(output.encode('utf-8', errors='replace'))
                        log_f.write(line)
                        log_f.flush()
                        self.process_game_output(line.strip())

                return_code = process.wait()
                self.running_process = None

                if return_code == 0:
                    self.log("游戏正常退出", "success")
                else:
                    self.log(f"游戏异常退出，返回码: {return_code}", "error")
                    self.show_crash_report(version)

        except Exception as e:
            error_msg = str(e)
            self.log(f"启动失败: {error_msg}", "error")
            self.log(traceback.format_exc(), "error")
            messagebox.showerror("错误", f"启动失败:\n{error_msg}")
        finally:
            self.set_status("就绪")
            self.toggle_buttons(True)

    def _build_fabric_command(self, java_path, memory_mb, version, version_data, natives_dir, username):
        """构建Fabric启动命令"""
        main_jar = os.path.join(self.minecraft_dir, 'versions', version, f"{version}.jar")

        # 查找Fabric loader主类
        fabric_loader_main_class = "net.fabricmc.loader.launch.knot.KnotClient"

        # 构建classpath
        libraries = []
        libraries_dir = os.path.join(self.minecraft_dir, 'libraries')

        for lib in version_data['libraries']:
            if 'downloads' in lib and 'artifact' in lib['downloads']:
                lib_path = os.path.join(
                    libraries_dir,
                    lib['downloads']['artifact']['path']
                )
                if os.path.exists(lib_path):
                    libraries.append(lib_path)

        classpath = os.pathsep.join([main_jar] + libraries)

        cmd = [
            java_path,
            f"-Xmx{memory_mb}M",
            f"-Xms{max(512, memory_mb // 2)}M",
            f"-Djava.library.path={natives_dir}",
            f"-Dminecraft.client.jar={main_jar}",
            "-cp", classpath,
            fabric_loader_main_class,
            "--username", username,
            "--version", version,
            "--gameDir", self.minecraft_dir,
            "--assetsDir", os.path.join(self.minecraft_dir, 'assets'),
            "--assetIndex", version_data['assets'],
            "--accessToken", "0",
            "--userType", "legacy",
            "--versionType", "release"
        ]

        # 添加Fabric特定参数
        cmd.extend([
            "-Dfabric.skipMcProvider=true",
            "-Dlog4j.configurationFile=client-1.12.xml"
        ])

        return cmd

    def _build_forge_command(self, java_path, memory_mb, version, version_data, natives_dir, username):
        """构建Forge启动命令"""
        main_jar = os.path.join(self.minecraft_dir, 'versions', version, f"{version}.jar")

        # 查找Forge主类
        forge_main_class = "net.minecraft.launchwrapper.Launch"

        # 构建classpath
        libraries = []
        libraries_dir = os.path.join(self.minecraft_dir, 'libraries')

        for lib in version_data['libraries']:
            if 'downloads' in lib and 'artifact' in lib['downloads']:
                lib_path = os.path.join(
                    libraries_dir,
                    lib['downloads']['artifact']['path']
                )
                if os.path.exists(lib_path):
                    libraries.append(lib_path)

        classpath = os.pathsep.join([main_jar] + libraries)

        cmd = [
            java_path,
            f"-Xmx{memory_mb}M",
            f"-Xms{max(512, memory_mb // 2)}M",
            f"-Djava.library.path={natives_dir}",
            f"-Dminecraft.client.jar={main_jar}",
            "-cp", classpath,
            forge_main_class,
            "--username", username,
            "--version", version,
            "--gameDir", self.minecraft_dir,
            "--assetsDir", os.path.join(self.minecraft_dir, 'assets'),
            "--assetIndex", version_data['assets'],
            "--accessToken", "0",
            "--userType", "legacy",
            "--versionType", "release",
            "--tweakClass", "net.minecraftforge.fml.common.launcher.FMLTweaker"
        ]

        # 添加Forge特定参数
        cmd.extend([
            "-Dfml.ignoreInvalidMinecraftCertificates=true",
            "-Dfml.ignorePatchDiscrepancies=true",
            "-Dlog4j.configurationFile=client-1.12.xml"
        ])

        return cmd

    def create_game_process(self, cmd):
        """创建游戏进程"""
        startupinfo = None
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        return subprocess.Popen(
            cmd,
            cwd=self.minecraft_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace',
            startupinfo=startupinfo
        )

    def safe_decode(self, byte_data):
        """安全解码字节数据"""
        encodings = ['utf-8', 'gbk', 'latin-1']
        for enc in encodings:
            try:
                return byte_data.decode(enc)
            except UnicodeDecodeError:
                continue
        return byte_data.decode('utf-8', errors='replace')

    def process_game_output(self, line):
        """处理游戏输出日志"""
        if not line:
            return

        # 根据内容类型添加不同标签
        if "ERROR" in line or "Exception" in line:
            self.log(line, "error")
        elif "WARN" in line:
            self.log(line, "warning")
        elif "Sound" in line and "missing" in line:  # 处理声音文件缺失警告
            self.log(line, "warning")
        else:
            self.log(line)

    def verify_game_files(self, version, version_data):
        """验证游戏文件完整性"""
        missing_files = []

        # 检查主JAR
        jar_path = os.path.join(self.minecraft_dir, 'versions', version, f"{version}.jar")
        if not os.path.exists(jar_path):
            missing_files.append(f"{version}.jar")

        # 检查资源索引
        assets_index_path = os.path.join(
            self.minecraft_dir,
            'assets',
            'indexes',
            f"{version_data['assets']}.json"
        )
        if not os.path.exists(assets_index_path):
            missing_files.append(f"assets/indexes/{version_data['assets']}.json")

        # 检查关键库文件
        libraries_dir = os.path.join(self.minecraft_dir, 'libraries')
        for lib in version_data['libraries']:
            if 'rules' in lib and not self.check_library_rules(lib['rules']):
                continue

            if 'downloads' not in lib or 'artifact' not in lib['downloads']:
                continue

            lib_path = os.path.join(
                libraries_dir,
                lib['downloads']['artifact']['path']
            )

            if not os.path.exists(lib_path):
                missing_files.append(lib['downloads']['artifact']['path'])

        return missing_files

    def repair_game_files(self, version, version_data, missing_files):
        """修复缺失的游戏文件"""
        mirror_url = self.get_mirror_url()

        try:
            self.log("尝试修复缺失文件...")

            # 修复主JAR
            jar_path = os.path.join(self.minecraft_dir, 'versions', version, f"{version}.jar")
            if f"{version}.jar" in missing_files:
                client_url = version_data['downloads']['client']['url']
                client_url = client_url.replace(
                    "https://launcher.mojang.com",
                    mirror_url
                )
                self.log(f"重新下载客户端: {client_url}")
                self.download_file(client_url, jar_path)

            # 修复资源索引
            assets_index_path = os.path.join(
                self.minecraft_dir,
                'assets',
                'indexes',
                f"{version_data['assets']}.json"
            )
            if f"assets/indexes/{version_data['assets']}.json" in missing_files:
                assets_url = version_data['assetIndex']['url']
                assets_url = assets_url.replace(
                    "https://launchermeta.mojang.com",
                    mirror_url
                )
                self.log(f"重新下载资源索引: {assets_url}")
                self.download_file(assets_url, assets_index_path)

            # 修复库文件
            libraries_dir = os.path.join(self.minecraft_dir, 'libraries')
            for lib in version_data['libraries']:
                if 'downloads' not in lib or 'artifact' not in lib['downloads']:
                    continue

                lib_path = os.path.join(
                    libraries_dir,
                    lib['downloads']['artifact']['path']
                )

                if lib['downloads']['artifact']['path'] in missing_files:
                    lib_url = lib['downloads']['artifact']['url']
                    lib_url = lib_url.replace(
                        "https://libraries.minecraft.net",
                        f"{mirror_url}/maven"
                    )
                    self.log(f"重新下载库: {lib_url}")
                    self.download_file(lib_url, lib_path)

            self.log("文件修复完成", "success")
            return True
        except Exception as e:
            self.log(f"修复文件失败: {str(e)}", "error")
            return False

    def show_crash_report(self, version):
        """显示崩溃报告"""
        crash_reports_dir = os.path.join(self.minecraft_dir, 'crash-reports')
        if not os.path.exists(crash_reports_dir):
            return

        # 查找最新的崩溃报告
        crash_reports = []
        for f in os.listdir(crash_reports_dir):
            if f.startswith('crash-') and f.endswith('.txt'):
                crash_reports.append(f)

        if not crash_reports:
            return

        latest_crash = max(crash_reports)
        crash_path = os.path.join(crash_reports_dir, latest_crash)

        try:
            with open(crash_path, 'r', encoding='utf-8') as f:
                crash_content = f.read()

            # 显示崩溃报告对话框
            crash_dialog = Toplevel(self.root)
            crash_dialog.title(f"崩溃报告 - {version}")
            crash_dialog.geometry("800x600")

            text_frame = ttk.Frame(crash_dialog)
            text_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

            text = Text(
                text_frame,
                wrap=WORD,
                bg="white",
                fg="#0066cc",
                font=('Consolas', 10))
            text.pack(side=LEFT, fill=BOTH, expand=True)

            scrollbar = ttk.Scrollbar(text_frame, command=text.yview)
            scrollbar.pack(side=RIGHT, fill=Y)
            text.config(yscrollcommand=scrollbar.set)

            text.insert(END, crash_content)
            text.config(state=DISABLED)

            button_frame = ttk.Frame(crash_dialog)
            button_frame.pack(fill=X, padx=10, pady=(0, 10))

            ttk.Button(
                button_frame,
                text="关闭",
                command=crash_dialog.destroy,
                style="Accent.TButton"
            ).pack(side=RIGHT)

            ttk.Button(
                button_frame,
                text="复制报告",
                command=lambda: self.root.clipboard_append(crash_content),
                style="Accent.TButton"
            ).pack(side=RIGHT, padx=5)
        except Exception as e:
            self.log(f"读取崩溃报告失败: {str(e)}", "error")

    def delete_version(self):
        """删除选中的版本"""
        selection = self.version_listbox.curselection()
        if not selection:
            messagebox.showerror("错误", "请选择要删除的版本")
            return

        version = self.version_listbox.get(selection[0])

        if not messagebox.askyesno("确认", f"确定要删除版本 {version} 吗？"):
            return

        version_dir = os.path.join(self.minecraft_dir, 'versions', version)
        try:
            if os.path.exists(version_dir):
                shutil.rmtree(version_dir)
                self.log(f"已删除版本: {version}", "success")
                self.refresh_local_versions()
            else:
                self.log(f"版本目录不存在: {version_dir}", "error")
        except Exception as e:
            self.log(f"删除版本失败: {str(e)}", "error")
            messagebox.showerror("错误", f"删除版本失败:\n{str(e)}")

    def install_fabric(self):
        """安装Fabric加载器"""
        selection = self.version_listbox.curselection()
        if not selection:
            messagebox.showerror("错误", "请先选择一个Minecraft版本")
            return

        base_version = self.version_listbox.get(selection[0])

        # 获取Fabric版本列表
        try:
            fabric_versions = self._get_fabric_versions()
            if not fabric_versions:
                messagebox.showerror("错误", "无法获取Fabric版本列表")
                return

            # 显示Fabric版本选择对话框
            selected_version = self._show_fabric_version_dialog(fabric_versions)
            if not selected_version:
                return

            # 在新线程中安装Fabric
            threading.Thread(
                target=self._install_fabric_thread,
                args=(base_version, selected_version),
                daemon=True
            ).start()

        except Exception as e:
            self.log(f"获取Fabric版本失败: {str(e)}", "error")
            messagebox.showerror("错误", f"获取Fabric版本失败:\n{str(e)}")

    def _show_fabric_version_dialog(self, fabric_versions):
        """显示Fabric版本选择对话框"""
        dialog = Toplevel(self.root)
        dialog.title("选择Fabric版本")
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中对话框
        window_width = 400
        window_height = 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 版本列表
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        listbox = Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            bg="white",
            fg="#0066cc",
            selectbackground="#4da6ff",
            selectforeground="white",
            font=('Consolas', 10)
        )
        listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # 填充版本列表
        for version in fabric_versions:
            listbox.insert(END, f"Fabric Loader {version['version']}")

        # 选择按钮
        selected_version = None

        def on_select():
            nonlocal selected_version
            selection = listbox.curselection()
            if selection:
                selected_version = fabric_versions[selection[0]]
                dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=X, padx=10, pady=(0, 10))

        ttk.Button(
            button_frame,
            text="选择",
            command=on_select,
            style="Accent.TButton"
        ).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="取消",
            command=dialog.destroy,
            style="Accent.TButton"
        ).pack(side=LEFT, fill=X, expand=True)

        dialog.wait_window()
        return selected_version

    def _get_fabric_versions(self):
        """获取Fabric版本列表"""
        try:
            # 直接使用Fabric官方API
            fabric_meta_url = "https://meta.fabricmc.net/v2/versions/loader"
            self.log(f"从Fabric官方API获取版本列表: {fabric_meta_url}")
            response = requests.get(fabric_meta_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log(f"无法从Fabric官方API获取版本列表: {str(e)}", "error")
            return None

    def _install_fabric_thread(self, base_version, fabric_version):
        """安装Fabric的线程"""
        try:
            self.set_status(f"正在安装Fabric {fabric_version['version']}...")
            self.log(f"开始安装Fabric {fabric_version['version']} 到 {base_version}")

            # 禁用按钮防止重复操作
            self.toggle_buttons(False)

            # 1. 获取Fabric安装配置
            fabric_profile_url = f"https://meta.fabricmc.net/v2/versions/loader/{base_version}/{fabric_version['version']}/profile/json"
            self.log(f"获取Fabric安装配置: {fabric_profile_url}")

            response = requests.get(fabric_profile_url, timeout=30)
            response.raise_for_status()

            fabric_profile = response.json()
            fabric_version_id = fabric_profile['id']

            # 2. 创建版本目录
            version_dir = os.path.join(self.minecraft_dir, 'versions', fabric_version_id)
            os.makedirs(version_dir, exist_ok=True)

            # 3. 保存Fabric版本json
            json_path = os.path.join(version_dir, f"{fabric_version_id}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(fabric_profile, f, indent=2, ensure_ascii=False)
            self.log(f"Fabric版本信息已保存: {json_path}")

            # 4. 下载Fabric相关库文件
            libraries_dir = os.path.join(self.minecraft_dir, 'libraries')
            os.makedirs(libraries_dir, exist_ok=True)

            mirror_url = self.get_mirror_url()

            for lib in fabric_profile['libraries']:
                if 'downloads' in lib and 'artifact' in lib['downloads']:
                    lib_url = lib['downloads']['artifact']['url']

                    # 尝试使用镜像源
                    if "maven.fabricmc.net" in lib_url:
                        mirror_lib_url = lib_url.replace(
                            "https://maven.fabricmc.net",
                            f"{mirror_url}/maven"
                        )
                        try:
                            self.download_file(mirror_lib_url,
                                               os.path.join(libraries_dir, lib['downloads']['artifact']['path']))
                            continue
                        except Exception as e:
                            self.log(f"从镜像源下载失败，尝试原始URL: {lib_url}", "warning")

                    # 使用原始URL
                    try:
                        self.download_file(lib_url, os.path.join(libraries_dir, lib['downloads']['artifact']['path']))
                    except Exception as e:
                        self.log(f"下载Fabric库失败: {lib_url} - {str(e)}", "error")
                        continue

            self.log(f"Fabric {fabric_version['version']} 安装完成!", "success")
            messagebox.showinfo("成功", f"Fabric {fabric_version['version']} 安装完成!")
            self.refresh_local_versions()

        except Exception as e:
            error_msg = str(e)
            self.log(f"安装Fabric失败: {error_msg}", "error")
            self.log(traceback.format_exc(), "error")
            messagebox.showerror("错误", f"安装Fabric失败:\n{error_msg}")
        finally:
            self.set_status("就绪")
            self.toggle_buttons(True)

    def install_forge(self):
        """安装Forge加载器"""
        selection = self.version_listbox.curselection()
        if not selection:
            messagebox.showerror("错误", "请先选择一个Minecraft版本")
            return

        base_version = self.version_listbox.get(selection[0])

        # 获取Forge版本列表
        try:
            forge_versions = self._get_forge_versions(base_version)
            if not forge_versions:
                messagebox.showerror("错误", "无法获取Forge版本列表")
                return

            # 显示Forge版本选择对话框
            selected_version = self._show_forge_version_dialog(forge_versions)
            if not selected_version:
                return

            # 在新线程中安装Forge
            threading.Thread(
                target=self._install_forge_thread,
                args=(base_version, selected_version),
                daemon=True
            ).start()

        except Exception as e:
            self.log(f"获取Forge版本失败: {str(e)}", "error")
            messagebox.showerror("错误", f"获取Forge版本失败:\n{str(e)}")

    def _get_forge_versions(self, minecraft_version):
        """获取Forge版本列表"""
        mirror_url = self.get_mirror_url()
        forge_meta_url = f"{mirror_url}/forge/minecraft/{minecraft_version}"

        response = requests.get(forge_meta_url, timeout=10)
        response.raise_for_status()

        return response.json()

    def _show_forge_version_dialog(self, forge_versions):
        """显示Forge版本选择对话框"""
        dialog = Toplevel(self.root)
        dialog.title("选择Forge版本")
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中对话框
        window_width = 400
        window_height = 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 版本列表
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        listbox = Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            bg="white",
            fg="#0066cc",
            selectbackground="#4da6ff",
            selectforeground="white",
            font=('Consolas', 10)
        )
        listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # 填充版本列表
        for version in forge_versions:
            listbox.insert(END, f"Forge {version['version']}")

        # 选择按钮
        selected_version = None

        def on_select():
            nonlocal selected_version
            selection = listbox.curselection()
            if selection:
                selected_version = forge_versions[selection[0]]
                dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=X, padx=10, pady=(0, 10))

        ttk.Button(
            button_frame,
            text="选择",
            command=on_select,
            style="Accent.TButton"
        ).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="取消",
            command=dialog.destroy,
            style="Accent.TButton"
        ).pack(side=LEFT, fill=X, expand=True)

        dialog.wait_window()
        return selected_version

    def _install_forge_thread(self, base_version, forge_version):
        """安装Forge的线程"""
        try:
            self.set_status(f"正在安装Forge {forge_version['version']}...")
            self.log(f"开始安装Forge {forge_version['version']} 到 {base_version}")

            # 禁用按钮防止重复操作
            self.toggle_buttons(False)

            # 1. 下载Forge安装器
            mirror_url = self.get_mirror_url()
            forge_installer_url = forge_version['url'].replace(
                "https://files.minecraftforge.net/maven",
                f"{mirror_url}/maven"
            )

            # 2. 下载Forge安装器
            installer_path = os.path.join(self.minecraft_dir, 'forge_installer.jar')
            self.log(f"下载Forge安装器: {forge_installer_url}")
            self.download_file(forge_installer_url, installer_path)

            # 3. 运行Forge安装器
            self.log("运行Forge安装器...")
            java_path = self.java_entry.get().strip()

            cmd = [
                java_path,
                "-jar", installer_path,
                "--installServer" if platform.system() == "Linux" else "--installClient",
                "--mirror", mirror_url
            ]

            process = subprocess.Popen(
                cmd,
                cwd=self.minecraft_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )

            # 读取安装器输出
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.log(output.strip())

            return_code = process.wait()

            if return_code != 0:
                raise Exception(f"Forge安装器返回错误代码: {return_code}")

            # 4. 清理安装器
            os.remove(installer_path)

            # 5. 检查安装结果
            forge_version_id = f"{base_version}-forge{forge_version['version']}"
            version_dir = os.path.join(self.minecraft_dir, 'versions', forge_version_id)

            if not os.path.exists(version_dir):
                raise Exception("Forge安装失败，版本目录未创建")

            self.log(f"Forge {forge_version['version']} 安装完成!", "success")
            messagebox.showinfo("成功", f"Forge {forge_version['version']} 安装完成!")
            self.refresh_local_versions()

        except Exception as e:
            error_msg = str(e)
            self.log(f"安装Forge失败: {error_msg}", "error")
            self.log(traceback.format_exc(), "error")
            messagebox.showerror("错误", f"安装Forge失败:\n{error_msg}")
        finally:
            self.set_status("就绪")
            self.toggle_buttons(True)

    def toggle_buttons(self, enable):
        """切换按钮状态"""
        state = NORMAL if enable else DISABLED
        self.download_btn.config(state=state)
        self.launch_btn.config(state=state)
        self.refresh_btn.config(state=state)

    def set_status(self, message):
        """设置状态栏文本"""
        self.status_label.config(text=message)
        self.root.update()

    def log(self, message, level="info"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        # 显示在UI
        self.log_text.insert(END, log_entry, level)
        self.log_text.see(END)

        # 写入文件
        with open(self.log_file, 'a', encoding='utf-8', errors='replace') as f:
            f.write(log_entry)

        self.root.update()

    def on_closing(self):
        """窗口关闭事件处理"""
        self.animations_running = False

        # 停止正在运行的进程
        if self.running_process and self.running_process.poll() is None:
            if messagebox.askyesno("确认", "游戏正在运行，确定要退出吗？"):
                self.running_process.terminate()

        self.save_config()
        self.root.destroy()


if __name__ == "__main__":
    root = Tk()
    launcher = MinecraftBlueLauncher(root)
    root.protocol("WM_DELETE_WINDOW", launcher.on_closing)
    root.mainloop()