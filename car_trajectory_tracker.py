#!/usr/bin/env python3
"""
小车轨迹跟踪程序
功能：从视频中选择并跟踪小车，绘制其运动轨迹

作者：Assistant
日期：2026-02-01
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
import os
import json
from typing import List, Tuple, Optional
import argparse

class CarTrajectoryTracker:
    def __init__(self, video_path: str):
        """
        初始化小车轨迹跟踪器
        
        Args:
            video_path: 视频文件路径
        """
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.trajectory = []  # 存储轨迹点 [(x, y, frame_num), ...]
        self.selected_bbox = None  # 选择的边界框 (x, y, w, h)
        self.tracker = None  # OpenCV跟踪器
        self.is_tracking = False
        
        # 鼠标选择相关
        self.selecting = False
        self.start_point = None
        self.current_frame = None
        
        print(f"视频信息:")
        print(f"  - 分辨率: {self.width}x{self.height}")
        print(f"  - 帧率: {self.fps} FPS")
        print(f"  - 总帧数: {self.total_frames}")
        print(f"  - 时长: {self.total_frames/self.fps:.2f}秒")
    
    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数，用于选择跟踪目标"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.selecting = True
            self.start_point = (x, y)
        
        elif event == cv2.EVENT_MOUSEMOVE and self.selecting:
            if self.current_frame is not None:
                temp_frame = self.current_frame.copy()
                cv2.rectangle(temp_frame, self.start_point, (x, y), (0, 255, 0), 2)
                cv2.imshow('Car Tracker', temp_frame)
        
        elif event == cv2.EVENT_LBUTTONUP and self.selecting:
            self.selecting = False
            if self.start_point:
                # 计算边界框
                x1, y1 = self.start_point
                x2, y2 = x, y
                
                # 确保坐标正确
                bbox_x = min(x1, x2)
                bbox_y = min(y1, y2)
                bbox_w = abs(x2 - x1)
                bbox_h = abs(y2 - y1)
                
                if bbox_w > 10 and bbox_h > 10:  # 确保选择区域足够大
                    self.selected_bbox = (bbox_x, bbox_y, bbox_w, bbox_h)
                    print(f"选择的区域: ({bbox_x}, {bbox_y}, {bbox_w}, {bbox_h})")
                    return True
        return False
    
    def select_target(self) -> bool:
        """
        让用户选择要跟踪的目标
        
        Returns:
            bool: 是否成功选择目标
        """
        print("\n请在视频窗口中用鼠标框选要跟踪的小车:")
        print("  - 点击并拖拽鼠标框选目标")
        print("  - 按ESC取消选择")
        print("  - 按空格键确认选择")
        
        # 读取第一帧
        ret, frame = self.cap.read()
        if not ret:
            print("无法读取视频第一帧")
            return False
        
        self.current_frame = frame.copy()
        cv2.namedWindow('Car Tracker', cv2.WINDOW_RESIZABLE)
        cv2.setMouseCallback('Car Tracker', self.mouse_callback)
        
        while True:
            display_frame = self.current_frame.copy()
            
            # 如果已选择区域，显示边界框
            if self.selected_bbox:
                x, y, w, h = self.selected_bbox
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(display_frame, "按空格确认选择, ESC取消", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(display_frame, "请用鼠标框选要跟踪的小车", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('Car Tracker', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' ') and self.selected_bbox:  # 空格确认
                break
            elif key == 27:  # ESC取消
                cv2.destroyAllWindows()
                return False
        
        cv2.destroyAllWindows()
        return self.selected_bbox is not None
    
    def init_tracker(self) -> bool:
        """
        初始化跟踪器
        
        Returns:
            bool: 是否成功初始化
        """
        if not self.selected_bbox:
            return False
        
        # 重置到第一帧
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.cap.read()
        if not ret:
            return False
        
        # 创建跟踪器 (使用CSRT跟踪器，效果较好)
        self.tracker = cv2.TrackerCSRT_create()
        
        # 初始化跟踪器
        success = self.tracker.init(frame, self.selected_bbox)
        if success:
            # 添加第一个轨迹点
            x, y, w, h = self.selected_bbox
            center_x = x + w // 2
            center_y = y + h // 2
            self.trajectory.append((center_x, center_y, 0))
            self.is_tracking = True
            print(f"跟踪器初始化成功!")
        
        return success
    
    def track_car(self, save_video: bool = False) -> List[Tuple[int, int, int]]:
        """
        跟踪小车并记录轨迹
        
        Args:
            save_video: 是否保存跟踪过程视频
            
        Returns:
            轨迹点列表 [(x, y, frame_num), ...]
        """
        if not self.is_tracking:
            print("跟踪器未初始化")
            return []
        
        print("开始跟踪...")
        
        # 如果需要保存视频
        out = None
        if save_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter('tracked_output.mp4', fourcc, self.fps, (self.width, self.height))
        
        frame_num = 0
        lost_frames = 0  # 连续丢失帧数
        max_lost_frames = 10  # 最大允许连续丢失帧数
        
        cv2.namedWindow('Tracking', cv2.WINDOW_RESIZABLE)
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            frame_num += 1
            
            # 更新跟踪器
            success, bbox = self.tracker.update(frame)
            
            if success:
                # 重置丢失计数
                lost_frames = 0
                
                # 提取边界框坐标
                x, y, w, h = map(int, bbox)
                center_x = x + w // 2
                center_y = y + h // 2
                
                # 添加到轨迹
                self.trajectory.append((center_x, center_y, frame_num))
                
                # 绘制边界框和轨迹
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, (center_x, center_y), 3, (0, 0, 255), -1)
                
                # 绘制轨迹线
                if len(self.trajectory) > 1:
                    for i in range(len(self.trajectory) - 1):
                        pt1 = (self.trajectory[i][0], self.trajectory[i][1])
                        pt2 = (self.trajectory[i + 1][0], self.trajectory[i + 1][1])
                        cv2.line(frame, pt1, pt2, (255, 0, 0), 2)
                
                # 显示信息
                info_text = f"Frame: {frame_num}/{self.total_frames} | Points: {len(self.trajectory)}"
                cv2.putText(frame, info_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, "按ESC停止跟踪", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
            else:
                lost_frames += 1
                cv2.putText(frame, f"跟踪失败 ({lost_frames}/{max_lost_frames})", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                if lost_frames >= max_lost_frames:
                    print(f"连续{max_lost_frames}帧跟踪失败，停止跟踪")
                    break
            
            # 显示帧
            cv2.imshow('Tracking', frame)
            
            # 保存帧
            if save_video and out:
                out.write(frame)
            
            # 检查退出键
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            
            # 显示进度
            if frame_num % (self.fps * 2) == 0:  # 每2秒显示一次进度
                progress = (frame_num / self.total_frames) * 100
                print(f"跟踪进度: {progress:.1f}% ({frame_num}/{self.total_frames})")
        
        cv2.destroyAllWindows()
        
        if save_video and out:
            out.release()
            print("跟踪视频已保存为 tracked_output.mp4")
        
        print(f"跟踪完成! 共记录 {len(self.trajectory)} 个轨迹点")
        return self.trajectory
    
    def plot_trajectory(self, save_path: str = "trajectory.png", show_plot: bool = True):
        """
        绘制轨迹图
        
        Args:
            save_path: 保存路径
            show_plot: 是否显示图形
        """
        if not self.trajectory:
            print("没有轨迹数据可绘制")
            return
        
        # 提取坐标和时间
        x_coords = [point[0] for point in self.trajectory]
        y_coords = [point[1] for point in self.trajectory]
        frames = [point[2] for point in self.trajectory]
        times = [frame / self.fps for frame in frames]  # 转换为时间(秒)
        
        # 创建图形
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 轨迹图
        ax1.plot(x_coords, y_coords, 'b-', linewidth=2, alpha=0.7, label='轨迹')
        ax1.scatter(x_coords[0], y_coords[0], color='green', s=100, label='起点', zorder=5)
        ax1.scatter(x_coords[-1], y_coords[-1], color='red', s=100, label='终点', zorder=5)
        
        # 添加方向箭头
        if len(x_coords) > 10:
            for i in range(0, len(x_coords) - 5, max(1, len(x_coords) // 10)):
                dx = x_coords[i + 5] - x_coords[i]
                dy = y_coords[i + 5] - y_coords[i]
                if dx != 0 or dy != 0:
                    ax1.arrow(x_coords[i], y_coords[i], dx * 0.3, dy * 0.3, 
                             head_width=15, head_length=20, fc='red', alpha=0.6)
        
        ax1.set_xlabel('X 坐标 (像素)')
        ax1.set_ylabel('Y 坐标 (像素)')
        ax1.set_title('小车运动轨迹')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_aspect('equal', adjustable='box')
        
        # 反转Y轴，因为图像坐标系Y轴向下
        ax1.invert_yaxis()
        
        # 时间-位移图
        distances = [0]
        for i in range(1, len(x_coords)):
            dist = np.sqrt((x_coords[i] - x_coords[i-1])**2 + (y_coords[i] - y_coords[i-1])**2)
            distances.append(distances[-1] + dist)
        
        ax2.plot(times, distances, 'g-', linewidth=2)
        ax2.set_xlabel('时间 (秒)')
        ax2.set_ylabel('累积距离 (像素)')
        ax2.set_title('时间-距离关系')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图片
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"轨迹图已保存为: {save_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()
    
    def save_trajectory_data(self, save_path: str = "trajectory_data.json"):
        """
        保存轨迹数据到文件
        
        Args:
            save_path: 保存路径
        """
        if not self.trajectory:
            print("没有轨迹数据可保存")
            return
        
        data = {
            "video_info": {
                "path": self.video_path,
                "width": self.width,
                "height": self.height,
                "fps": self.fps,
                "total_frames": self.total_frames
            },
            "trajectory": self.trajectory,
            "selected_bbox": self.selected_bbox
        }
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"轨迹数据已保存为: {save_path}")
    
    def analyze_motion(self):
        """分析运动特性"""
        if len(self.trajectory) < 2:
            print("轨迹点不足，无法分析运动")
            return
        
        # 计算速度和加速度
        velocities = []
        accelerations = []
        
        for i in range(1, len(self.trajectory)):
            x1, y1, t1 = self.trajectory[i-1]
            x2, y2, t2 = self.trajectory[i]
            
            dt = (t2 - t1) / self.fps  # 时间差(秒)
            if dt > 0:
                dx = x2 - x1
                dy = y2 - y1
                velocity = np.sqrt(dx**2 + dy**2) / dt  # 像素/秒
                velocities.append(velocity)
        
        for i in range(1, len(velocities)):
            dv = velocities[i] - velocities[i-1]
            dt = 1.0 / self.fps
            acceleration = dv / dt
            accelerations.append(acceleration)
        
        # 统计信息
        total_distance = 0
        for i in range(1, len(self.trajectory)):
            x1, y1, _ = self.trajectory[i-1]
            x2, y2, _ = self.trajectory[i]
            total_distance += np.sqrt((x2-x1)**2 + (y2-y1)**2)
        
        total_time = len(self.trajectory) / self.fps
        avg_velocity = total_distance / total_time if total_time > 0 else 0
        
        print("\n=== 运动分析结果 ===")
        print(f"总轨迹点数: {len(self.trajectory)}")
        print(f"总运动时间: {total_time:.2f} 秒")
        print(f"总运动距离: {total_distance:.2f} 像素")
        print(f"平均速度: {avg_velocity:.2f} 像素/秒")
        
        if velocities:
            print(f"最大速度: {max(velocities):.2f} 像素/秒")
            print(f"最小速度: {min(velocities):.2f} 像素/秒")
        
        if accelerations:
            print(f"最大加速度: {max(accelerations):.2f} 像素/秒²")
            print(f"最小加速度: {min(accelerations):.2f} 像素/秒²")
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='小车轨迹跟踪程序')
    parser.add_argument('video_path', help='视频文件路径')
    parser.add_argument('--save-video', action='store_true', help='保存跟踪过程视频')
    parser.add_argument('--output-dir', default='.', help='输出目录')
    
    args = parser.parse_args()
    
    # 检查视频文件是否存在
    if not os.path.exists(args.video_path):
        print(f"错误: 视频文件不存在: {args.video_path}")
        return
    
    try:
        # 创建跟踪器
        tracker = CarTrajectoryTracker(args.video_path)
        
        # 选择目标
        if not tracker.select_target():
            print("未选择目标，程序退出")
            return
        
        # 初始化跟踪器
        if not tracker.init_tracker():
            print("跟踪器初始化失败")
            return
        
        # 开始跟踪
        trajectory = tracker.track_car(save_video=args.save_video)
        
        if trajectory:
            # 创建输出目录
            os.makedirs(args.output_dir, exist_ok=True)
            
            # 绘制轨迹图
            trajectory_plot_path = os.path.join(args.output_dir, "car_trajectory.png")
            tracker.plot_trajectory(trajectory_plot_path)
            
            # 保存轨迹数据
            trajectory_data_path = os.path.join(args.output_dir, "car_trajectory_data.json")
            tracker.save_trajectory_data(trajectory_data_path)
            
            # 运动分析
            tracker.analyze_motion()
            
            print(f"\n轨迹跟踪完成!")
            print(f"  - 轨迹图: {trajectory_plot_path}")
            print(f"  - 数据文件: {trajectory_data_path}")
            if args.save_video:
                print(f"  - 跟踪视频: tracked_output.mp4")
        else:
            print("没有获取到有效轨迹")
    
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()