#!/usr/bin/env python3
"""
小车轨迹跟踪程序 - 图形界面版本

使用tkinter创建简单易用的图形界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import os
import json
from datetime import datetime
import queue
import time
from PIL import Image, ImageTk

# 导入增强跟踪器
try:
    from advanced_tracker import EnhancedTracker, check_yolo_available, get_tracker_info
    ADVANCED_TRACKER_AVAILABLE = True
except ImportError:
    ADVANCED_TRACKER_AVAILABLE = False
    
# 检查YOLO是否可用
YOLO_AVAILABLE = False
if ADVANCED_TRACKER_AVAILABLE:
    YOLO_AVAILABLE = check_yolo_available()

class CarTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("小车轨迹跟踪程序")
        self.root.geometry("800x600")
        
        # 数据
        self.video_path = None
        self.cap = None
        self.tracker = None
        self.trajectory = []
        self.selected_bbox = None
        self.is_tracking = False
        self.tracking_thread = None
        
        # 跟踪方法选择
        self.tracking_method = tk.StringVar(value="enhanced")  # 默认使用增强跟踪
        self.reverse_tracking = tk.BooleanVar(value=False)  # 反向跟踪选项
        
        # UI控件
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="请选择视频文件")
        
        # 消息队列，用于线程间通信
        self.message_queue = queue.Queue()
        
        self.setup_ui()
        self.check_queue()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="视频文件", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="选择视频", command=self.select_video).grid(row=0, column=0, padx=5)
        self.file_label = ttk.Label(file_frame, text="未选择文件", foreground="gray")
        self.file_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # 控制按钮区域
        control_frame = ttk.LabelFrame(main_frame, text="操作控制", padding="5")
        control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 跟踪方法选择
        method_frame = ttk.LabelFrame(main_frame, text="跟踪方法", padding="5")
        method_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Radiobutton(method_frame, text="简单模板匹配", value="simple", 
                       variable=self.tracking_method).grid(row=0, column=0, padx=10)
        
        enhanced_text = "增强跟踪 (卡尔曼滤波+外观模型)"
        if not ADVANCED_TRACKER_AVAILABLE:
            enhanced_text += " [不可用]"
        ttk.Radiobutton(method_frame, text=enhanced_text, value="enhanced", 
                       variable=self.tracking_method,
                       state='normal' if ADVANCED_TRACKER_AVAILABLE else 'disabled').grid(row=0, column=1, padx=10)
        
        yolo_text = "YOLO深度学习 (最稳定)"
        if not YOLO_AVAILABLE:
            yolo_text += " [需安装ultralytics]"
        self.yolo_radio = ttk.Radiobutton(method_frame, text=yolo_text, value="yolo", 
                       variable=self.tracking_method,
                       state='normal' if YOLO_AVAILABLE else 'disabled')
        self.yolo_radio.grid(row=0, column=2, padx=10)
        
        # 安装YOLO按钮
        if not YOLO_AVAILABLE and ADVANCED_TRACKER_AVAILABLE:
            ttk.Button(method_frame, text="安装YOLO", 
                      command=self.install_yolo).grid(row=0, column=3, padx=10)
        
        # 反向跟踪选项
        ttk.Separator(method_frame, orient='vertical').grid(row=0, column=4, sticky='ns', padx=15)
        self.reverse_check = ttk.Checkbutton(method_frame, text="反向跟踪（从视频末尾开始）", 
                                             variable=self.reverse_tracking)
        self.reverse_check.grid(row=0, column=5, padx=10)
        
        # 按钮
        self.select_btn = ttk.Button(control_frame, text="选择跟踪目标", 
                                   command=self.select_target, state='disabled')
        self.select_btn.grid(row=0, column=0, padx=5, pady=2)
        
        self.manual_select_btn = ttk.Button(control_frame, text="手动选择", 
                                          command=self.manual_select_target, state='disabled')
        self.manual_select_btn.grid(row=0, column=1, padx=5, pady=2)
        
        self.track_btn = ttk.Button(control_frame, text="开始跟踪", 
                                  command=self.start_tracking, state='disabled')
        self.track_btn.grid(row=0, column=2, padx=5, pady=2)
        
        self.stop_btn = ttk.Button(control_frame, text="停止跟踪", 
                                 command=self.stop_tracking, state='disabled')
        self.stop_btn.grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Button(control_frame, text="查看轨迹", command=self.show_trajectory).grid(row=1, column=0, padx=5, pady=2)
        ttk.Button(control_frame, text="保存数据", command=self.save_data).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(control_frame, text="导出视频", command=self.export_video).grid(row=1, column=2, padx=5, pady=2)
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        
        # 状态显示
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="5")
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, wrap=tk.WORD)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 统计信息
        stats_frame = ttk.LabelFrame(main_frame, text="跟踪统计", padding="5")
        stats_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="轨迹点: 0 | 距离: 0.0 | 时间: 0.0s")
        self.stats_label.grid(row=0, column=0, sticky=tk.W)
        
        # 配置主框架权重
        main_frame.rowconfigure(4, weight=1)
        
        # 显示跟踪器状态
        tracker_status = "可用跟踪方法: 简单模板匹配"
        if ADVANCED_TRACKER_AVAILABLE:
            tracker_status += ", 增强跟踪"
        if YOLO_AVAILABLE:
            tracker_status += ", YOLO深度学习"
        self.log_message(tracker_status)
        self.log_message("程序启动完成，请选择视频文件开始使用")
    
    def install_yolo(self):
        """安装YOLO (ultralytics)"""
        global YOLO_AVAILABLE
        
        result = messagebox.askyesno("安装YOLO", 
            "是否安装ultralytics库（包含YOLOv8）？\n\n"
            "这将需要下载约100MB的包，以及首次使用时下载模型文件。\n"
            "安装后需要重启程序。")
        
        if result:
            self.log_message("正在安装ultralytics...")
            
            def install_thread():
                import subprocess
                try:
                    subprocess.check_call(['pip', 'install', 'ultralytics'])
                    self.message_queue.put(("info", "ultralytics安装成功！请重启程序以启用YOLO跟踪。"))
                    messagebox.showinfo("安装成功", "ultralytics安装成功！\n请重启程序以启用YOLO跟踪。")
                except Exception as e:
                    self.message_queue.put(("error", f"安装失败: {e}"))
            
            threading.Thread(target=install_thread, daemon=True).start()

    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.status_text.insert(tk.END, log_entry)
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def select_video(self):
        """选择视频文件"""
        filetypes = (
            ('视频文件', '*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm'),
            ('MP4文件', '*.mp4'),
            ('AVI文件', '*.avi'),
            ('所有文件', '*.*')
        )
        
        filename = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=filetypes
        )
        
        if filename:
            self.video_path = filename
            self.file_label.config(text=os.path.basename(filename), foreground="black")
            
            # 检查视频信息
            try:
                self.cap = cv2.VideoCapture(filename)
                if not self.cap.isOpened():
                    raise ValueError("无法打开视频文件")
                
                fps = int(self.cap.get(cv2.CAP_PROP_FPS))
                frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration = frame_count / fps if fps > 0 else 0
                
                self.log_message(f"视频加载成功:")
                self.log_message(f"  分辨率: {width}x{height}")
                self.log_message(f"  帧率: {fps} FPS")
                self.log_message(f"  时长: {duration:.1f}秒 ({frame_count}帧)")
                
                self.select_btn.config(state='normal')
                self.manual_select_btn.config(state='normal')
                
            except Exception as e:
                messagebox.showerror("错误", f"无法加载视频文件:\n{str(e)}")
                self.video_path = None
                self.file_label.config(text="文件加载失败", foreground="red")
    
    def select_target(self):
        """选择跟踪目标 - 使用tkinter实现"""
        if not self.cap:
            return
        
        self.log_message("正在打开目标选择窗口...")
        
        # 根据跟踪方向选择起始帧
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if self.reverse_tracking.get():
            # 反向跟踪：从最后一帧选择
            start_frame = total_frames - 1
            self.log_message(f"反向跟踪模式：在最后一帧(帧{start_frame})选择目标")
        else:
            # 正向跟踪：从第一帧选择
            start_frame = 0
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("错误", f"无法读取视频帧{start_frame}")
            return
        
        # 创建目标选择窗口
        self.create_target_selection_window(frame, start_frame)
    
    def create_target_selection_window(self, frame, frame_num=0):
        """创建目标选择窗口"""
        # 转换OpenCV图像为PIL格式
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 计算缩放比例，限制窗口大小
        height, width = frame_rgb.shape[:2]
        max_width, max_height = 800, 600
        scale = min(max_width/width, max_height/height, 1.0)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # 缩放图像
        frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
        
        # 转换为PIL Image然后为PhotoImage
        pil_image = Image.fromarray(frame_resized)
        photo = ImageTk.PhotoImage(pil_image)
        
        # 创建选择窗口
        select_window = tk.Toplevel(self.root)
        title = "选择跟踪目标"
        if self.reverse_tracking.get():
            title += f" [反向跟踪 - 帧{frame_num}]"
        else:
            title += f" [帧{frame_num}]"
        select_window.title(title)
        select_window.transient(self.root)
        select_window.grab_set()
        
        # 窗口居中 - 增加高度确保按钮可见
        window_width = new_width + 40
        window_height = new_height + 150  # 增加更多空间给按钮
        x = (select_window.winfo_screenwidth() // 2) - (window_width // 2)
        y = (select_window.winfo_screenheight() // 2) - (window_height // 2)
        select_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 说明标签
        info_frame = ttk.Frame(select_window)
        info_frame.pack(pady=5)
        ttk.Label(info_frame, text="用鼠标拖拽选择要跟踪的小车区域", 
                 font=("Arial", 12)).pack()
        ttk.Label(info_frame, text="选择完成后点击确认按钮", 
                 foreground="blue").pack()
        
        # 创建Canvas显示图像
        canvas = tk.Canvas(select_window, width=new_width, height=new_height,
                          cursor="crosshair", bg="white")
        canvas.pack(pady=5)
        
        # 在Canvas上显示图像
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        canvas.image = photo  # 保持引用
        
        # 选择相关变量
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
        self.scale_factor = scale
        self.original_frame_size = (width, height)
        self.temp_selected_bbox = None
        
        # 先创建按钮框架和按钮（需要在鼠标事件之前）
        # 坐标显示
        self.coord_label = ttk.Label(select_window, text="请框选车辆（红点标记轨迹中心位置）", 
                                    font=("Arial", 11, "bold"))
        self.coord_label.pack(pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(select_window)
        button_frame.pack(pady=15)
        
        # 确认按钮（初始禁用）- 使用更大的样式
        style = ttk.Style()
        style.configure("Big.TButton", font=("Arial", 11), padding=10)
        
        confirm_btn = ttk.Button(button_frame, text="✓ 确认选择", 
                                state='disabled', style="Big.TButton")
        confirm_btn.pack(side=tk.LEFT, padx=15)
        
        cancel_btn = ttk.Button(button_frame, text="✗ 取消", style="Big.TButton")
        cancel_btn.pack(side=tk.LEFT, padx=15)
        
        reset_btn = ttk.Button(button_frame, text="↺ 重新选择", style="Big.TButton")
        reset_btn.pack(side=tk.LEFT, padx=15)
        
        def on_mouse_press(event):
            self.selection_start = (event.x, event.y)
            self.selection_end = None
            if self.selection_rect:
                canvas.delete(self.selection_rect)
                self.selection_rect = None
            confirm_btn.config(state='disabled')
        
        def on_mouse_drag(event):
            if self.selection_start:
                if self.selection_rect:
                    canvas.delete(self.selection_rect)
                
                x1, y1 = self.selection_start
                x2, y2 = event.x, event.y
                
                # 确保矩形在画布范围内
                x2 = max(0, min(new_width, x2))
                y2 = max(0, min(new_height, y2))
                
                self.selection_rect = canvas.create_rectangle(
                    x1, y1, x2, y2, outline="red", width=2)
                self.selection_end = (x2, y2)
        
        def on_mouse_release(event):
            if self.selection_start:
                x1, y1 = self.selection_start
                x2, y2 = event.x, event.y
                
                # 确保在画布范围内
                x2 = max(0, min(new_width, x2))
                y2 = max(0, min(new_height, y2))
                
                self.selection_end = (x2, y2)
                
                # 确保左上角和右下角正确
                left = min(x1, x2)
                top = min(y1, y2)
                right = max(x1, x2)
                bottom = max(y1, y2)
                
                sel_width = right - left
                sel_height = bottom - top
                
                if sel_width > 10 and sel_height > 10:  # 确保选择区域足够大
                    # 转换回原始图像坐标
                    orig_left = int(left / scale)
                    orig_top = int(top / scale)
                    orig_width = int(sel_width / scale)
                    orig_height = int(sel_height / scale)
                    
                    self.temp_selected_bbox = (orig_left, orig_top, orig_width, orig_height)
                    
                    # 在canvas上标记选择区域（绿色表示有效）
                    if self.selection_rect:
                        canvas.delete(self.selection_rect)
                    if hasattr(self, 'center_marker') and self.center_marker:
                        canvas.delete(self.center_marker)
                    if hasattr(self, 'center_cross_h') and self.center_cross_h:
                        canvas.delete(self.center_cross_h)
                    if hasattr(self, 'center_cross_v') and self.center_cross_v:
                        canvas.delete(self.center_cross_v)
                    
                    self.selection_rect = canvas.create_rectangle(
                        left, top, right, bottom, outline="green", width=3)
                    
                    # 绘制中心点标记（红色十字+圆点）
                    center_x = (left + right) // 2
                    center_y = (top + bottom) // 2
                    cross_size = 15
                    self.center_marker = canvas.create_oval(
                        center_x - 5, center_y - 5, center_x + 5, center_y + 5,
                        fill="red", outline="white", width=2)
                    self.center_cross_h = canvas.create_line(
                        center_x - cross_size, center_y, center_x + cross_size, center_y,
                        fill="red", width=2)
                    self.center_cross_v = canvas.create_line(
                        center_x, center_y - cross_size, center_x, center_y + cross_size,
                        fill="red", width=2)
                    
                    # 计算原始图像中的中心点坐标
                    orig_center_x = orig_left + orig_width // 2
                    orig_center_y = orig_top + orig_height // 2
                    
                    # 显示坐标信息（包含中心点）
                    self.coord_label.config(
                        text=f"✓ 区域: ({orig_left},{orig_top}) {orig_width}x{orig_height} | 中心: ({orig_center_x},{orig_center_y})")
                    
                    # 启用确认按钮
                    confirm_btn.config(state='normal')
                else:
                    self.coord_label.config(text="选择区域太小，请重新选择")
                    confirm_btn.config(state='disabled')
        
        def confirm_selection():
            if self.temp_selected_bbox:
                self.selected_bbox = self.temp_selected_bbox
                self.log_message(f"已选择目标区域: {self.selected_bbox}")
                self.track_btn.config(state='normal')
                select_window.destroy()
            else:
                messagebox.showwarning("警告", "请先选择一个区域")
        
        def cancel_selection():
            select_window.destroy()
        
        def reset_selection():
            if self.selection_rect:
                canvas.delete(self.selection_rect)
                self.selection_rect = None
            if hasattr(self, 'center_marker') and self.center_marker:
                canvas.delete(self.center_marker)
                self.center_marker = None
            if hasattr(self, 'center_cross_h') and self.center_cross_h:
                canvas.delete(self.center_cross_h)
                self.center_cross_h = None
            if hasattr(self, 'center_cross_v') and self.center_cross_v:
                canvas.delete(self.center_cross_v)
                self.center_cross_v = None
            self.selection_start = None
            self.selection_end = None
            self.temp_selected_bbox = None
            self.coord_label.config(text="请选择区域（红点为轨迹中心）...")
            confirm_btn.config(state='disabled')
        
        # 绑定按钮命令
        confirm_btn.config(command=confirm_selection)
        cancel_btn.config(command=cancel_selection)
        reset_btn.config(command=reset_selection)
        
        # 绑定鼠标事件
        canvas.bind("<Button-1>", on_mouse_press)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_release)
    
    def manual_select_target(self):
        """手动输入目标区域坐标"""
        if not self.cap:
            return
        
        # 创建输入对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("手动输入目标区域")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 获取视频尺寸作为参考
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 说明标签
        info_label = ttk.Label(dialog, text=f"视频尺寸: {width}x{height}\n请输入目标区域的左上角坐标和宽高:")
        info_label.pack(pady=10)
        
        # 输入框架
        input_frame = ttk.Frame(dialog)
        input_frame.pack(pady=10)
        
        # 坐标输入
        ttk.Label(input_frame, text="X坐标:").grid(row=0, column=0, sticky=tk.W)
        x_entry = ttk.Entry(input_frame, width=10)
        x_entry.grid(row=0, column=1, padx=5)
        x_entry.insert(0, str(width//4))  # 默认值
        
        ttk.Label(input_frame, text="Y坐标:").grid(row=1, column=0, sticky=tk.W)
        y_entry = ttk.Entry(input_frame, width=10)
        y_entry.grid(row=1, column=1, padx=5)
        y_entry.insert(0, str(height//4))
        
        ttk.Label(input_frame, text="宽度:").grid(row=2, column=0, sticky=tk.W)
        w_entry = ttk.Entry(input_frame, width=10)
        w_entry.grid(row=2, column=1, padx=5)
        w_entry.insert(0, str(width//8))
        
        ttk.Label(input_frame, text="高度:").grid(row=3, column=0, sticky=tk.W)
        h_entry = ttk.Entry(input_frame, width=10)
        h_entry.grid(row=3, column=1, padx=5)
        h_entry.insert(0, str(height//8))
        
        def confirm_selection():
            try:
                x = int(x_entry.get())
                y = int(y_entry.get())
                w = int(w_entry.get())
                h = int(h_entry.get())
                
                # 验证坐标
                if x < 0 or y < 0 or w <= 0 or h <= 0:
                    messagebox.showerror("错误", "坐标和尺寸必须为正数")
                    return
                
                if x + w > width or y + h > height:
                    messagebox.showerror("错误", "区域超出视频范围")
                    return
                
                self.selected_bbox = (x, y, w, h)
                self.log_message(f"手动设置目标区域: {self.selected_bbox}")
                self.track_btn.config(state='normal')
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
        
        # 按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="确认", command=confirm_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # 居中显示对话框
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        x_entry.focus()
    
    def start_tracking(self):
        """开始跟踪"""
        if not self.cap or not self.selected_bbox:
            return
        
        self.is_tracking = True
        self.trajectory = []
        
        # 禁用相关按钮
        self.select_btn.config(state='disabled')
        self.manual_select_btn.config(state='disabled')
        self.track_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        self.log_message("开始跟踪...")
        
        # 在新线程中运行跟踪
        self.tracking_thread = threading.Thread(target=self.tracking_worker)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
    
    def tracking_worker(self):
        """跟踪工作线程 - 支持多种跟踪方法和反向跟踪"""
        method = self.tracking_method.get()
        reverse = self.reverse_tracking.get()
        
        self.message_queue.put(("info", f"使用跟踪方法: {method}"))
        if reverse:
            self.message_queue.put(("info", "反向跟踪模式：从视频末尾开始"))
        
        try:
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            # 根据跟踪方向设置起始帧
            if reverse:
                start_frame = total_frames - 1
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            else:
                start_frame = 0
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            ret, frame = self.cap.read()
            if not ret:
                self.message_queue.put(("error", "无法读取视频帧"))
                return
            
            # 获取帧尺寸
            frame_height, frame_width = frame.shape[:2]
            self.message_queue.put(("info", f"视频帧尺寸: {frame_width}x{frame_height}"))
            
            # 获取初始bbox
            x, y, w, h = [int(v) for v in self.selected_bbox]
            self.message_queue.put(("info", f"选择的区域: ({x}, {y}, {w}, {h})"))
            
            # 根据方法初始化跟踪器
            if method == "enhanced" and ADVANCED_TRACKER_AVAILABLE:
                tracker = EnhancedTracker(frame, (x, y, w, h), use_deep_learning=False)
                self.message_queue.put(("info", "初始化增强跟踪器（卡尔曼滤波+外观模型）"))
            elif method == "yolo" and YOLO_AVAILABLE:
                tracker = EnhancedTracker(frame, (x, y, w, h), use_deep_learning=True)
                self.message_queue.put(("info", "初始化YOLO深度学习跟踪器"))
            else:
                # 简单模板匹配
                tracker = None
                template = frame[y:y+h, x:x+w].copy()
                self.message_queue.put(("info", f"使用简单模板匹配，模板尺寸: {template.shape[1]}x{template.shape[0]}"))
            
            # 添加第一个轨迹点
            center_x, center_y = x + w // 2, y + h // 2
            self.trajectory.append((center_x, center_y, start_frame))
            
            frame_num = start_frame
            frames_processed = 0
            
            # 简单模板匹配的搜索范围
            search_margin = 100
            
            # 创建显示窗口
            window_name = "实时跟踪 - 按ESC停止"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            
            # 计算显示尺寸
            display_scale = min(1280 / frame_width, 720 / frame_height, 1.0)
            display_width = int(frame_width * display_scale)
            display_height = int(frame_height * display_scale)
            cv2.resizeWindow(window_name, display_width, display_height)
            
            self.message_queue.put(("info", "开始跟踪...按ESC停止"))
            
            confidence = 1.0  # 跟踪置信度
            
            # 反向跟踪时的循环条件
            def should_continue():
                if reverse:
                    return self.is_tracking and frame_num > 0
                else:
                    return self.is_tracking and frame_num < total_frames - 1
            
            while should_continue():
                # 反向跟踪需要手动设置帧位置
                if reverse:
                    frame_num -= 1
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                    ret, frame = self.cap.read()
                else:
                    ret, frame = self.cap.read()
                    frame_num += 1
                
                if not ret:
                    break
                
                frames_processed += 1
                
                # 根据方法进行跟踪
                if tracker is not None:
                    # 使用增强跟踪器
                    success, bbox, confidence = tracker.update(frame)
                    
                    if success:
                        x, y, w, h = [int(v) for v in bbox]
                        center_x = x + w // 2
                        center_y = y + h // 2
                        self.trajectory.append((center_x, center_y, frame_num))
                    else:
                        # 跟踪失败，记录最后位置
                        self.trajectory.append((center_x, center_y, frame_num))
                        self.message_queue.put(("info", f"帧 {frame_num}: 跟踪丢失"))
                else:
                    # 简单模板匹配
                    search_x1 = max(0, x - search_margin)
                    search_y1 = max(0, y - search_margin)
                    search_x2 = min(frame_width, x + w + search_margin)
                    search_y2 = min(frame_height, y + h + search_margin)
                    
                    search_region = frame[search_y1:search_y2, search_x1:search_x2]
                    
                    if search_region.shape[0] < h or search_region.shape[1] < w:
                        self.trajectory.append((center_x, center_y, frame_num))
                    else:
                        result = cv2.matchTemplate(search_region, template, cv2.TM_CCOEFF_NORMED)
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                        confidence = max_val
                        
                        x = search_x1 + max_loc[0]
                        y = search_y1 + max_loc[1]
                        
                        center_x = x + w // 2
                        center_y = y + h // 2
                        self.trajectory.append((center_x, center_y, frame_num))
                        
                        if max_val > 0.6 and frame_num % 30 == 0:
                            template = frame[y:y+h, x:x+w].copy()
                
                # 更新进度
                progress = (frames_processed / total_frames) * 100
                distance = self.calculate_total_distance()
                time_elapsed = frames_processed / fps if fps > 0 else 0
                
                self.message_queue.put(("progress", {
                    "progress": progress,
                    "points": len(self.trajectory),
                    "distance": distance,
                    "time": time_elapsed,
                    "frame": frame_num
                }))
                
                # ===== 实时绘制轨迹 =====
                display_frame = frame.copy()
                
                # 绘制跟踪框 - 根据置信度改变颜色
                if confidence > 0.6:
                    box_color = (0, 255, 0)  # 绿色 - 高置信度
                elif confidence > 0.4:
                    box_color = (0, 255, 255)  # 黄色 - 中等置信度
                else:
                    box_color = (0, 0, 255)  # 红色 - 低置信度
                
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), box_color, 3)
                
                # 绘制中心点
                cv2.circle(display_frame, (center_x, center_y), 8, (0, 0, 255), -1)
                
                # 绘制轨迹线（美化版本）
                if len(self.trajectory) > 1:
                    for i in range(len(self.trajectory) - 1):
                        pt1 = (self.trajectory[i][0], self.trajectory[i][1])
                        pt2 = (self.trajectory[i + 1][0], self.trajectory[i + 1][1])
                        ratio = i / len(self.trajectory)
                        r = int(255 * ratio)
                        g = int(200 * (1 - ratio * 0.5))
                        b = int(255 * (1 - ratio))
                        color = (b, g, r)
                        cv2.line(display_frame, pt1, pt2, color, 16, cv2.LINE_AA)
                
                # 显示信息
                method_name = {"simple": "模板匹配", "enhanced": "增强跟踪", "yolo": "YOLO"}.get(method, method)
                direction_text = " [反向]" if reverse else ""
                info_text = f"Frame: {frame_num}/{total_frames} | {method_name}{direction_text}"
                cv2.putText(display_frame, info_text, (10, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                conf_text = f"Confidence: {confidence:.2f}"
                cv2.putText(display_frame, conf_text, (10, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, box_color, 2)
                
                # 显示尺度信息（如果使用增强跟踪器）
                if tracker is not None and hasattr(tracker, 'current_scale'):
                    scale_text = f"Scale: {tracker.current_scale:.2f}x | Box: {w}x{h}"
                    cv2.putText(display_frame, scale_text, (10, 120), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 100), 2)
                    cv2.putText(display_frame, "Press ESC to stop", (10, 160), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                else:
                    cv2.putText(display_frame, "Press ESC to stop", (10, 120), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                # 缩放显示
                if display_scale < 1.0:
                    display_frame = cv2.resize(display_frame, (display_width, display_height))
                
                cv2.imshow(window_name, display_frame)
                
                # 检查按键
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    self.message_queue.put(("info", "用户按ESC停止跟踪"))
                    break
                
                # 每秒更新一次日志
                if frames_processed % fps == 0:
                    direction = "←" if reverse else "→"
                    self.message_queue.put(("info", f"跟踪进度 {direction}: 帧{frame_num}/{total_frames}, 置信度: {confidence:.2f}"))
            
            cv2.destroyAllWindows()
            
            # 如果是反向跟踪，按帧号排序轨迹（确保时间顺序正确）
            if reverse and len(self.trajectory) > 1:
                self.trajectory.sort(key=lambda p: p[2])  # 按帧号排序
                self.message_queue.put(("info", "轨迹已按时间顺序重新排列"))
            
            self.message_queue.put(("complete", len(self.trajectory)))
            
        except Exception as e:
            import traceback
            error_msg = f"跟踪过程出错: {str(e)}\n{traceback.format_exc()}"
            self.message_queue.put(("error", error_msg))
    
    def calculate_total_distance(self):
        """计算总距离"""
        if len(self.trajectory) < 2:
            return 0.0
        
        total = 0.0
        for i in range(1, len(self.trajectory)):
            x1, y1, _ = self.trajectory[i-1]
            x2, y2, _ = self.trajectory[i]
            total += np.sqrt((x2-x1)**2 + (y2-y1)**2)
        return total
    
    def stop_tracking(self):
        """停止跟踪"""
        self.is_tracking = False
        self.log_message("正在停止跟踪...")
        
        # 等待跟踪线程结束
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=2.0)
        
        # 恢复按钮状态
        self.select_btn.config(state='normal')
        self.manual_select_btn.config(state='normal')
        self.track_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        
        self.log_message("跟踪已停止")
    
    def check_queue(self):
        """检查消息队列"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "progress":
                    self.progress_var.set(data["progress"])
                    self.stats_label.config(
                        text=f"轨迹点: {data['points']} | 距离: {data['distance']:.1f} | "
                             f"时间: {data['time']:.1f}s | 帧: {data['frame']}"
                    )
                elif msg_type == "info":
                    self.log_message(data)
                elif msg_type == "error":
                    self.log_message(f"错误: {data}")
                    messagebox.showerror("错误", data)
                    self.stop_tracking()
                elif msg_type == "complete":
                    self.log_message(f"跟踪完成! 共记录 {data} 个轨迹点")
                    self.stop_tracking()
                    messagebox.showinfo("完成", f"跟踪完成!\n共记录 {data} 个轨迹点")
                    
        except queue.Empty:
            pass
        
        # 继续检查
        self.root.after(100, self.check_queue)
    
    def show_trajectory(self):
        """显示轨迹图"""
        if not self.trajectory:
            messagebox.showwarning("警告", "没有轨迹数据")
            return
        
        # 创建新窗口显示轨迹
        traj_window = tk.Toplevel(self.root)
        traj_window.title("轨迹图")
        traj_window.geometry("800x600")
        
        # 创建matplotlib图形
        fig = Figure(figsize=(10, 6), dpi=80)
        
        # 轨迹图
        ax1 = fig.add_subplot(121)
        x_coords = [point[0] for point in self.trajectory]
        y_coords = [point[1] for point in self.trajectory]
        
        ax1.plot(x_coords, y_coords, 'b-', linewidth=2, alpha=0.7, label='轨迹')
        ax1.scatter(x_coords[0], y_coords[0], color='green', s=100, label='起点', zorder=5)
        ax1.scatter(x_coords[-1], y_coords[-1], color='red', s=100, label='终点', zorder=5)
        
        ax1.set_xlabel('X坐标 (像素)')
        ax1.set_ylabel('Y坐标 (像素)')
        ax1.set_title('小车运动轨迹')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.invert_yaxis()  # 反转Y轴
        ax1.set_aspect('equal', adjustable='box')
        
        # 时间-距离图
        ax2 = fig.add_subplot(122)
        if self.cap:
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            times = [point[2] / fps for point in self.trajectory]
            distances = [0]
            for i in range(1, len(x_coords)):
                dist = np.sqrt((x_coords[i] - x_coords[i-1])**2 + (y_coords[i] - y_coords[i-1])**2)
                distances.append(distances[-1] + dist)
            
            ax2.plot(times, distances, 'g-', linewidth=2)
            ax2.set_xlabel('时间 (秒)')
            ax2.set_ylabel('累积距离 (像素)')
            ax2.set_title('时间-距离关系')
            ax2.grid(True, alpha=0.3)
        
        # 将图形嵌入tkinter窗口
        canvas = FigureCanvasTkAgg(fig, traj_window)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 添加保存按钮
        save_frame = ttk.Frame(traj_window)
        save_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(save_frame, text="保存图片", 
                  command=lambda: self.save_trajectory_image(fig)).pack(side=tk.LEFT, padx=5)
    
    def save_trajectory_image(self, fig):
        """保存轨迹图片"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG文件", "*.png"), ("JPG文件", "*.jpg"), ("所有文件", "*.*")]
        )
        if filename:
            fig.savefig(filename, dpi=300, bbox_inches='tight')
            self.log_message(f"轨迹图已保存: {filename}")
    
    def save_data(self):
        """保存轨迹数据"""
        if not self.trajectory:
            messagebox.showwarning("警告", "没有轨迹数据")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                data = {
                    "video_path": self.video_path,
                    "trajectory": self.trajectory,
                    "selected_bbox": self.selected_bbox,
                    "timestamp": datetime.now().isoformat(),
                    "total_points": len(self.trajectory),
                    "total_distance": self.calculate_total_distance()
                }
                
                if filename.endswith('.json'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    # 保存为文本格式
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write("# 小车轨迹数据\n")
                        f.write(f"# 视频: {self.video_path}\n")
                        f.write(f"# 时间: {data['timestamp']}\n")
                        f.write("# 格式: 帧号 X坐标 Y坐标\n")
                        for i, (x, y, frame) in enumerate(self.trajectory):
                            f.write(f"{frame} {x} {y}\n")
                
                self.log_message(f"数据已保存: {filename}")
                messagebox.showinfo("成功", "数据保存完成!")
                
            except Exception as e:
                messagebox.showerror("错误", f"保存数据时出错:\n{str(e)}")
    
    def export_video(self):
        """导出带轨迹的视频"""
        if not self.trajectory:
            messagebox.showwarning("警告", "没有轨迹数据，请先完成跟踪")
            return
        
        if not self.video_path or not self.cap:
            messagebox.showwarning("警告", "没有视频文件")
            return
        
        # 打开轨迹参数设置对话框
        self.show_export_settings_dialog()
    
    def show_export_settings_dialog(self):
        """显示导出设置对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("导出视频设置")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.minsize(700, 500)
        
        # 配置网格权重，使窗口可缩放
        dialog.columnconfigure(0, weight=0)
        dialog.columnconfigure(1, weight=1)
        dialog.rowconfigure(0, weight=1)
        
        # 默认参数
        self.export_params = {
            'glow_width': tk.IntVar(value=80),
            'glow_blur': tk.IntVar(value=35),
            'glow_alpha': tk.DoubleVar(value=0.4),
            'core_width': tk.IntVar(value=32),
            'highlight_width': tk.IntVar(value=10),
            'smooth_window': tk.IntVar(value=5)
        }
        
        # 防抖定时器
        self.preview_update_id = None
        
        def schedule_preview_update(v=None):
            """防抖更新预览"""
            if self.preview_update_id:
                dialog.after_cancel(self.preview_update_id)
            self.preview_update_id = dialog.after(200, self.update_preview)
        
        # 左侧：参数设置
        left_frame = ttk.LabelFrame(dialog, text="轨迹参数", padding="10")
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")
        
        # 线宽设置（合并显示）
        ttk.Label(left_frame, text="═══ 线条宽度 ═══", font=("Arial", 9, "bold")).grid(row=0, column=0, columnspan=3, pady=(0,5))
        
        ttk.Label(left_frame, text="总线宽:").grid(row=1, column=0, sticky="w", pady=2)
        core_width_scale = ttk.Scale(left_frame, from_=2, to=120, length=150,
                                     variable=self.export_params['core_width'],
                                     command=schedule_preview_update)
        core_width_scale.grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Label(left_frame, textvariable=self.export_params['core_width'], width=4).grid(row=1, column=2)
        
        ttk.Label(left_frame, text="高光宽度:").grid(row=2, column=0, sticky="w", pady=2)
        highlight_scale = ttk.Scale(left_frame, from_=0, to=50, length=150,
                                    variable=self.export_params['highlight_width'],
                                    command=schedule_preview_update)
        highlight_scale.grid(row=2, column=1, sticky="ew", padx=5)
        ttk.Label(left_frame, textvariable=self.export_params['highlight_width'], width=4).grid(row=2, column=2)
        
        # 发光设置
        ttk.Label(left_frame, text="═══ 发光效果 ═══", font=("Arial", 9, "bold")).grid(row=3, column=0, columnspan=3, pady=(10,5))
        
        ttk.Label(left_frame, text="发光范围:").grid(row=4, column=0, sticky="w", pady=2)
        glow_width_scale = ttk.Scale(left_frame, from_=0, to=200, length=150,
                                     variable=self.export_params['glow_width'],
                                     command=schedule_preview_update)
        glow_width_scale.grid(row=4, column=1, sticky="ew", padx=5)
        ttk.Label(left_frame, textvariable=self.export_params['glow_width'], width=4).grid(row=4, column=2)
        
        ttk.Label(left_frame, text="发光强度:").grid(row=5, column=0, sticky="w", pady=2)
        alpha_label = ttk.Label(left_frame, text="0.3", width=4)
        glow_alpha_scale = ttk.Scale(left_frame, from_=0.0, to=1.0, length=150,
                                     variable=self.export_params['glow_alpha'])
        glow_alpha_scale.grid(row=5, column=1, sticky="ew", padx=5)
        alpha_label.grid(row=5, column=2)
        
        def update_alpha_label(v):
            alpha_label.config(text=f"{float(v):.1f}")
            schedule_preview_update()
        glow_alpha_scale.config(command=update_alpha_label)
        
        # 平滑设置
        ttk.Label(left_frame, text="═══ 其他设置 ═══", font=("Arial", 9, "bold")).grid(row=6, column=0, columnspan=3, pady=(10,5))
        
        ttk.Label(left_frame, text="轨迹平滑:").grid(row=7, column=0, sticky="w", pady=2)
        smooth_scale = ttk.Scale(left_frame, from_=1, to=15, length=150,
                                 variable=self.export_params['smooth_window'],
                                 command=schedule_preview_update)
        smooth_scale.grid(row=7, column=1, sticky="ew", padx=5)
        ttk.Label(left_frame, textvariable=self.export_params['smooth_window'], width=4).grid(row=7, column=2)
        
        # 预设按钮
        ttk.Label(left_frame, text="═══ 快速预设 ═══", font=("Arial", 9, "bold")).grid(row=8, column=0, columnspan=3, pady=(10,5))
        
        preset_frame = ttk.Frame(left_frame)
        preset_frame.grid(row=9, column=0, columnspan=3, pady=5)
        
        def apply_preset(glow_w, glow_a, core_w, hl_w, smooth):
            self.export_params['glow_width'].set(glow_w)
            self.export_params['glow_alpha'].set(glow_a)
            self.export_params['core_width'].set(core_w)
            self.export_params['highlight_width'].set(hl_w)
            self.export_params['smooth_window'].set(smooth)
            alpha_label.config(text=f"{glow_a:.1f}")
            self.update_preview()
        
        ttk.Button(preset_frame, text="细线", width=6,
                   command=lambda: apply_preset(20, 0.2, 8, 2, 3)).grid(row=0, column=0, padx=2)
        ttk.Button(preset_frame, text="中等", width=6,
                   command=lambda: apply_preset(40, 0.3, 16, 4, 5)).grid(row=0, column=1, padx=2)
        ttk.Button(preset_frame, text="粗线", width=6,
                   command=lambda: apply_preset(60, 0.4, 30, 8, 5)).grid(row=1, column=0, padx=2, pady=2)
        ttk.Button(preset_frame, text="无发光", width=6,
                   command=lambda: apply_preset(0, 0.0, 16, 4, 5)).grid(row=1, column=1, padx=2, pady=2)
        
        # 右侧：预览
        right_frame = ttk.LabelFrame(dialog, text="预览", padding="5")
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        # 预览画布 - 使用Label更简单
        self.preview_label = ttk.Label(right_frame, text="加载预览中...", anchor="center")
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        
        # 预览帧选择
        preview_control = ttk.Frame(right_frame)
        preview_control.grid(row=1, column=0, sticky="ew", pady=5)
        preview_control.columnconfigure(1, weight=1)
        
        ttk.Label(preview_control, text="预览帧:").grid(row=0, column=0)
        self.preview_frame_var = tk.IntVar(value=min(len(self.trajectory) // 2, len(self.trajectory)))
        preview_frame_scale = ttk.Scale(preview_control, from_=1, to=max(1, len(self.trajectory)), 
                                        variable=self.preview_frame_var,
                                        command=schedule_preview_update)
        preview_frame_scale.grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Button(preview_control, text="刷新", width=6,
                   command=self.update_preview).grid(row=0, column=2)
        
        # 底部按钮
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        def on_export():
            dialog.destroy()
            self.do_export_video()
        
        ttk.Button(button_frame, text="✓ 确认导出", width=12, command=on_export).pack(side="left", padx=10)
        ttk.Button(button_frame, text="✗ 取消", width=12, command=dialog.destroy).pack(side="left", padx=10)
        
        # 存储对话框和预览图像引用
        self.export_dialog = dialog
        self.preview_photo = None
        
        # 窗口居中
        dialog.update_idletasks()
        w = max(700, dialog.winfo_reqwidth())
        h = max(500, dialog.winfo_reqheight())
        x = (dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        
        # 初始预览
        dialog.after(100, self.update_preview)
    
    def update_preview(self):
        """更新预览图像"""
        try:
            if not hasattr(self, 'preview_label') or not self.preview_label.winfo_exists():
                return
            
            # 读取指定帧
            preview_frame_idx = self.preview_frame_var.get()
            
            # 找到对应的视频帧
            if preview_frame_idx > 0 and preview_frame_idx <= len(self.trajectory):
                video_frame_num = self.trajectory[preview_frame_idx - 1][2]
            else:
                video_frame_num = 0
            
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, video_frame_num)
            ret, frame = self.cap.read()
            if not ret:
                return
            
            # 先缩放帧以提高性能
            h, w = frame.shape[:2]
            max_size = 500
            scale = min(max_size / w, max_size / h, 1.0)
            if scale < 1.0:
                new_w, new_h = int(w * scale), int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))
            else:
                new_w, new_h = w, h
            
            # 获取参数
            glow_width = int(self.export_params['glow_width'].get() * scale)
            glow_blur = int(self.export_params['glow_blur'].get() * scale)
            glow_alpha = self.export_params['glow_alpha'].get()
            core_width = max(1, int(self.export_params['core_width'].get() * scale))
            highlight_width = max(1, int(self.export_params['highlight_width'].get() * scale))
            smooth_window = self.export_params['smooth_window'].get()
            
            # 确保模糊核是奇数且至少为1
            if glow_blur < 1:
                glow_blur = 1
            if glow_blur % 2 == 0:
                glow_blur += 1
            
            # 平滑轨迹（缩放坐标）
            smoothed_raw = self.smooth_trajectory(self.trajectory[:preview_frame_idx], smooth_window)
            smoothed = [(int(p[0] * scale), int(p[1] * scale), p[2]) for p in smoothed_raw]
            
            # 绘制轨迹
            if len(smoothed) > 1 and glow_width > 0 and glow_alpha > 0:
                glow_layer = np.zeros_like(frame, dtype=np.uint8)
                
                for i in range(len(smoothed) - 1):
                    pt1 = (smoothed[i][0], smoothed[i][1])
                    pt2 = (smoothed[i + 1][0], smoothed[i + 1][1])
                    
                    ratio = i / len(smoothed)
                    r = int(255 * ratio)
                    g = int(200 * (1 - ratio * 0.5))
                    b = int(255 * (1 - ratio))
                    color = (b, g, r)
                    
                    cv2.line(glow_layer, pt1, pt2, color, glow_width, cv2.LINE_AA)
                
                glow_layer = cv2.GaussianBlur(glow_layer, (glow_blur, glow_blur), 0)
                frame = cv2.addWeighted(glow_layer, glow_alpha, frame, 1.0, 0)
            
            # 核心线
            if len(smoothed) > 1 and core_width > 0:
                for i in range(len(smoothed) - 1):
                    pt1 = (smoothed[i][0], smoothed[i][1])
                    pt2 = (smoothed[i + 1][0], smoothed[i + 1][1])
                    
                    ratio = i / len(smoothed)
                    r = int(255 * ratio + 100 * (1 - ratio))
                    g = int(240 * (1 - ratio * 0.2))
                    b = int(255 * (1 - ratio))
                    r = min(255, r)
                    g = min(255, g)
                    color = (b, g, r)
                    
                    cv2.line(frame, pt1, pt2, color, core_width, cv2.LINE_AA)
            
            # 高光
            if len(smoothed) > 1 and highlight_width > 0:
                for i in range(len(smoothed) - 1):
                    pt1 = (smoothed[i][0], smoothed[i][1])
                    pt2 = (smoothed[i + 1][0], smoothed[i + 1][1])
                    cv2.line(frame, pt1, pt2, (255, 255, 255), highlight_width, cv2.LINE_AA)
            
            # 当前位置标记
            if smoothed:
                last_x, last_y = smoothed[-1][0], smoothed[-1][1]
                marker_size = max(3, int(8 * scale))
                cv2.circle(frame, (last_x, last_y), marker_size, (0, 255, 200), -1, cv2.LINE_AA)
                cv2.circle(frame, (last_x, last_y), max(2, marker_size//2), (255, 255, 255), -1, cv2.LINE_AA)
            
            # 转换为PhotoImage
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            self.preview_photo = ImageTk.PhotoImage(pil_image)
            
            # 更新标签
            self.preview_label.config(image=self.preview_photo, text="")
            
        except Exception as e:
            print(f"预览更新错误: {e}")
    
    def do_export_video(self):
        """执行视频导出"""
        # 选择保存路径
        filename = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4视频", "*.mp4"), ("AVI视频", "*.avi"), ("所有文件", "*.*")],
            initialfile="trajectory_video.mp4"
        )
        
        if not filename:
            return
        
        self.log_message("开始导出视频...")
        
        # 获取参数
        params = {
            'glow_width': self.export_params['glow_width'].get(),
            'glow_blur': self.export_params['glow_blur'].get(),
            'glow_alpha': self.export_params['glow_alpha'].get(),
            'core_width': self.export_params['core_width'].get(),
            'highlight_width': self.export_params['highlight_width'].get(),
            'smooth_window': self.export_params['smooth_window'].get()
        }
        
        # 在新线程中导出
        export_thread = threading.Thread(target=self.export_video_worker, args=(filename, params))
        export_thread.daemon = True
        export_thread.start()
    
    def export_video_worker(self, output_path, params=None):
        """视频导出工作线程"""
        try:
            # 默认参数
            if params is None:
                params = {
                    'glow_width': 48,
                    'glow_blur': 25,
                    'glow_alpha': 0.3,
                    'core_width': 20,
                    'highlight_width': 6,
                    'smooth_window': 5
                }
            
            # 确保模糊核是奇数
            glow_blur = params['glow_blur']
            if glow_blur % 2 == 0:
                glow_blur += 1
            
            # 重新打开视频
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.message_queue.put(("error", "无法打开视频文件"))
                return
            
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 首先对轨迹进行平滑处理
            smoothed_trajectory = self.smooth_trajectory(self.trajectory, window_size=params['smooth_window'])
            
            # 使用ffmpeg命令行导出高质量视频（如果可用）
            use_ffmpeg = False
            temp_path = None
            
            # 先尝试用OpenCV写入，使用最高质量设置
            # 优先使用无损或高质量编码器
            final_path = output_path
            if output_path.lower().endswith('.mp4'):
                final_path = output_path
            else:
                final_path = os.path.splitext(output_path)[0] + '.avi'
            
            # 使用MJPG编码器获得更高质量（文件会大一些但质量好）
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            avi_path = os.path.splitext(output_path)[0] + '.avi'
            out = cv2.VideoWriter(avi_path, fourcc, fps, (frame_width, frame_height))
            
            if not out.isOpened():
                # 备选方案
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                out = cv2.VideoWriter(avi_path, fourcc, fps, (frame_width, frame_height))
            
            if not out.isOpened():
                self.message_queue.put(("error", "无法创建输出视频文件"))
                cap.release()
                return
            
            self.message_queue.put(("info", f"正在导出高质量视频: {total_frames} 帧, {frame_width}x{frame_height}"))
            self.message_queue.put(("info", f"轨迹参数: 发光={params['glow_width']}, 核心={params['core_width']}, 高光={params['highlight_width']}"))
            
            frame_num = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 找到当前帧之前的所有轨迹点（使用平滑后的轨迹）
                current_trajectory = []
                for tx, ty, tf in smoothed_trajectory:
                    if tf <= frame_num:
                        current_trajectory.append((tx, ty, tf))
                
                # 绘制美化轨迹
                if len(current_trajectory) > 1:
                    # ===== 第一层：外层发光（模糊效果）=====
                    if params['glow_width'] > 0 and params['glow_alpha'] > 0:
                        glow_layer = np.zeros_like(frame, dtype=np.uint8)
                        
                        for i in range(len(current_trajectory) - 1):
                            pt1 = (int(current_trajectory[i][0]), int(current_trajectory[i][1]))
                            pt2 = (int(current_trajectory[i + 1][0]), int(current_trajectory[i + 1][1]))
                            
                            ratio = i / len(current_trajectory)
                            r = int(255 * ratio)
                            g = int(200 * (1 - ratio * 0.5))
                            b = int(255 * (1 - ratio))
                            color = (b, g, r)
                            
                            cv2.line(glow_layer, pt1, pt2, color, params['glow_width'], cv2.LINE_AA)
                        
                        # 对发光层进行高斯模糊实现平滑效果
                        glow_layer = cv2.GaussianBlur(glow_layer, (glow_blur, glow_blur), 0)
                        
                        # 混合发光层
                        frame = cv2.addWeighted(glow_layer, params['glow_alpha'], frame, 1.0, 0)
                    
                    # ===== 第二层：核心轨迹线 =====
                    if params['core_width'] > 0:
                        for i in range(len(current_trajectory) - 1):
                            pt1 = (int(current_trajectory[i][0]), int(current_trajectory[i][1]))
                            pt2 = (int(current_trajectory[i + 1][0]), int(current_trajectory[i + 1][1]))
                            
                            ratio = i / len(current_trajectory)
                            r = int(255 * ratio + 100 * (1 - ratio))
                            g = int(240 * (1 - ratio * 0.2))
                            b = int(255 * (1 - ratio))
                            r = min(255, r)
                            g = min(255, g)
                            color = (b, g, r)
                            
                            cv2.line(frame, pt1, pt2, color, params['core_width'], cv2.LINE_AA)
                    
                    # ===== 第三层：高光核心 =====
                    if params['highlight_width'] > 0:
                        for i in range(len(current_trajectory) - 1):
                            pt1 = (int(current_trajectory[i][0]), int(current_trajectory[i][1]))
                            pt2 = (int(current_trajectory[i + 1][0]), int(current_trajectory[i + 1][1]))
                            # 白色高光
                            cv2.line(frame, pt1, pt2, (255, 255, 255), params['highlight_width'], cv2.LINE_AA)
                
                # 绘制当前位置标记
                if current_trajectory:
                    last_x, last_y = int(current_trajectory[-1][0]), int(current_trajectory[-1][1])
                    cv2.circle(frame, (last_x, last_y), 12, (0, 255, 200), -1, cv2.LINE_AA)
                    cv2.circle(frame, (last_x, last_y), 6, (255, 255, 255), -1, cv2.LINE_AA)
                
                # 绘制起点标记
                if smoothed_trajectory:
                    start_x, start_y = int(smoothed_trajectory[0][0]), int(smoothed_trajectory[0][1])
                    cv2.circle(frame, (start_x, start_y), 18, (0, 255, 0), 4, cv2.LINE_AA)
                    cv2.circle(frame, (start_x, start_y), 12, (100, 255, 100), -1, cv2.LINE_AA)
                
                # 添加半透明信息背景
                overlay = frame.copy()
                cv2.rectangle(overlay, (10, 10), (420, 90), (0, 0, 0), -1)
                frame = cv2.addWeighted(overlay, 0.4, frame, 0.6, 0)
                
                cv2.putText(frame, f"Frame: {frame_num}/{total_frames}", (20, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Trajectory Points: {len(current_trajectory)}", (20, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
                
                # 写入帧
                out.write(frame)
                
                frame_num += 1
                
                # 更新进度
                if frame_num % 10 == 0:
                    progress = (frame_num / total_frames) * 100
                    self.message_queue.put(("progress", {
                        "progress": progress,
                        "points": len(current_trajectory),
                        "distance": self.calculate_total_distance(),
                        "time": frame_num / fps,
                        "frame": frame_num
                    }))
            
            # 释放资源
            cap.release()
            out.release()
            
            # 如果用户想要mp4格式，尝试用ffmpeg转换
            if output_path.lower().endswith('.mp4') and avi_path != output_path:
                try:
                    import subprocess
                    # 尝试使用ffmpeg转换为高质量mp4
                    cmd = [
                        'ffmpeg', '-y', '-i', avi_path,
                        '-c:v', 'libx264', '-crf', '18', '-preset', 'slow',
                        '-pix_fmt', 'yuv420p', output_path
                    ]
                    result = subprocess.run(cmd, capture_output=True, timeout=300)
                    if result.returncode == 0:
                        os.remove(avi_path)  # 删除临时avi文件
                        self.message_queue.put(("info", f"视频已转换为高质量MP4: {output_path}"))
                    else:
                        # ffmpeg失败，保留avi
                        self.message_queue.put(("info", f"MP4转换失败，已保存为AVI: {avi_path}"))
                        output_path = avi_path
                except Exception as e:
                    # ffmpeg不可用，保留avi
                    self.message_queue.put(("info", f"已保存为AVI格式: {avi_path}"))
                    output_path = avi_path
            else:
                output_path = avi_path
            
            self.message_queue.put(("info", f"视频导出完成: {output_path}"))
            self.message_queue.put(("progress", {"progress": 100, "points": len(self.trajectory), 
                                                "distance": self.calculate_total_distance(), 
                                                "time": total_frames/fps, "frame": total_frames}))
            
            # 弹出完成提示
            final_output = output_path
            self.root.after(100, lambda: messagebox.showinfo("完成", f"视频导出成功!\n保存位置: {final_output}"))
            
        except Exception as e:
            import traceback
            self.message_queue.put(("error", f"导出视频出错: {str(e)}\n{traceback.format_exc()}"))
    
    def smooth_trajectory(self, trajectory, window_size=5):
        """对轨迹进行平滑处理（移动平均）"""
        if len(trajectory) < window_size:
            return trajectory
        
        smoothed = []
        half_window = window_size // 2
        
        for i in range(len(trajectory)):
            start_idx = max(0, i - half_window)
            end_idx = min(len(trajectory), i + half_window + 1)
            
            # 计算窗口内的平均值
            avg_x = sum(trajectory[j][0] for j in range(start_idx, end_idx)) / (end_idx - start_idx)
            avg_y = sum(trajectory[j][1] for j in range(start_idx, end_idx)) / (end_idx - start_idx)
            
            smoothed.append((avg_x, avg_y, trajectory[i][2]))  # 保持原始帧号
        
        return smoothed

def main():
    """主函数"""
    root = tk.Tk()
    app = CarTrackerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()