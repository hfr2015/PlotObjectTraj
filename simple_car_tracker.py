"""
简易版小车轨迹跟踪程序 - 适用于初学者

这个版本的程序更加简洁，功能相对简化，便于理解和使用。

功能：
1. 加载视频
2. 手动选择小车
3. 跟踪轨迹
4. 绘制轨迹图

使用方法：
python simple_car_tracker.py your_video.mp4
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

class SimpleCarTracker:
    def __init__(self, video_path):
        """初始化跟踪器"""
        self.cap = cv2.VideoCapture(video_path)
        self.trajectory = []  # 轨迹点列表
        self.selected_area = None  # 选择的区域
        self.tracker = None  # 跟踪器
        
        # 检查视频是否成功打开
        if not self.cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        print("视频加载成功!")
        print(f"视频尺寸: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
        print(f"总帧数: {int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))}")
    
    def select_car(self):
        """让用户选择要跟踪的小车"""
        print("\n请在视频窗口中框选要跟踪的小车:")
        print("1. 用鼠标拖拽框选小车")
        print("2. 按空格键确认选择")
        print("3. 按ESC键退出")
        
        # 读取第一帧
        ret, frame = self.cap.read()
        if not ret:
            print("无法读取视频帧")
            return False
        
        # 让用户选择区域
        bbox = cv2.selectROI("选择要跟踪的小车", frame, False)
        cv2.destroyAllWindows()
        
        # 检查是否成功选择
        if bbox[2] > 0 and bbox[3] > 0:
            self.selected_area = bbox
            print(f"已选择区域: {bbox}")
            return True
        else:
            print("未选择有效区域")
            return False
    
    def track_car(self):
        """跟踪小车并记录轨迹"""
        if self.selected_area is None:
            print("请先选择要跟踪的区域")
            return False
        
        # 重置到第一帧
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.cap.read()
        if not ret:
            return False
        
        # 创建跟踪器
        self.tracker = cv2.TrackerCSRT_create()
        
        # 初始化跟踪器
        if not self.tracker.init(frame, self.selected_area):
            print("跟踪器初始化失败")
            return False
        
        print("开始跟踪... 按ESC键停止")
        
        frame_count = 0
        cv2.namedWindow('Car Tracking', cv2.WINDOW_RESIZABLE)
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("视频播放完毕")
                break
            
            frame_count += 1
            
            # 更新跟踪器
            success, bbox = self.tracker.update(frame)
            
            if success:
                # 获取小车中心点
                x, y, w, h = map(int, bbox)
                center_x = x + w // 2
                center_y = y + h // 2
                
                # 记录轨迹点
                self.trajectory.append((center_x, center_y))
                
                # 画出边界框和中心点
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, (center_x, center_y), 3, (0, 0, 255), -1)
                
                # 画出轨迹线
                if len(self.trajectory) > 1:
                    for i in range(len(self.trajectory) - 1):
                        pt1 = self.trajectory[i]
                        pt2 = self.trajectory[i + 1]
                        cv2.line(frame, pt1, pt2, (255, 0, 0), 2)
                
                # 显示信息
                cv2.putText(frame, f"Frame: {frame_count}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"Points: {len(self.trajectory)}", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            else:
                # 跟踪失败
                cv2.putText(frame, "Tracking Lost!", (10, 110), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # 显示帧
            cv2.imshow('Car Tracking', frame)
            
            # 检查按键
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC键退出
                break
        
        cv2.destroyAllWindows()
        print(f"跟踪完成! 共记录了 {len(self.trajectory)} 个轨迹点")
        return True
    
    def plot_trajectory(self):
        """绘制轨迹图"""
        if not self.trajectory:
            print("没有轨迹数据")
            return
        
        # 提取x和y坐标
        x_coords = [point[0] for point in self.trajectory]
        y_coords = [point[1] for point in self.trajectory]
        
        # 创建图形
        plt.figure(figsize=(10, 8))
        
        # 绘制轨迹
        plt.plot(x_coords, y_coords, 'b-', linewidth=2, label='轨迹')
        plt.scatter(x_coords[0], y_coords[0], color='green', s=100, label='起点')
        plt.scatter(x_coords[-1], y_coords[-1], color='red', s=100, label='终点')
        
        # 设置图形属性
        plt.xlabel('X坐标 (像素)')
        plt.ylabel('Y坐标 (像素)')
        plt.title('小车运动轨迹')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 反转Y轴（图像坐标系）
        plt.gca().invert_yaxis()
        
        # 设置相等的坐标轴比例
        plt.axis('equal')
        
        # 保存并显示图形
        plt.savefig('car_trajectory_simple.png', dpi=300, bbox_inches='tight')
        print("轨迹图已保存为: car_trajectory_simple.png")
        plt.show()
    
    def save_data(self, filename='trajectory_simple.txt'):
        """保存轨迹数据到文本文件"""
        if not self.trajectory:
            print("没有数据可保存")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 小车轨迹数据\n")
            f.write("# 格式: 帧序号 X坐标 Y坐标\n")
            for i, (x, y) in enumerate(self.trajectory):
                f.write(f"{i+1} {x} {y}\n")
        
        print(f"轨迹数据已保存为: {filename}")
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("使用方法: python simple_car_tracker.py <视频文件>")
        print("例如: python simple_car_tracker.py my_video.mp4")
        return
    
    video_path = sys.argv[1]
    
    # 检查文件是否存在
    if not os.path.exists(video_path):
        print(f"错误: 找不到视频文件 '{video_path}'")
        return
    
    try:
        # 创建跟踪器
        print("正在初始化跟踪器...")
        tracker = SimpleCarTracker(video_path)
        
        # 选择要跟踪的小车
        if not tracker.select_car():
            print("程序退出")
            return
        
        # 开始跟踪
        if tracker.track_car():
            # 绘制轨迹
            tracker.plot_trajectory()
            
            # 保存数据
            tracker.save_data()
            
            print("\n=== 跟踪完成 ===")
            print("轨迹图: car_trajectory_simple.png")
            print("数据文件: trajectory_simple.txt")
        
    except Exception as e:
        print(f"程序出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()