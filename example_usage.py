"""
示例和测试脚本

这个脚本演示如何使用轨迹跟踪器的各种功能
也可以用于测试程序是否正常工作
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# 添加当前目录到路径，以便导入模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from car_trajectory_tracker import CarTrajectoryTracker
except ImportError:
    print("无法导入 car_trajectory_tracker 模块")
    print("请确保文件 car_trajectory_tracker.py 存在于当前目录")
    sys.exit(1)


def create_test_video():
    """创建一个测试视频，包含一个移动的方块"""
    print("正在创建测试视频...")
    
    # 视频参数
    width, height = 640, 480
    fps = 30
    duration = 10  # 秒
    total_frames = fps * duration
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('test_video.mp4', fourcc, fps, (width, height))
    
    # 小车参数
    car_size = 30
    car_color = (0, 255, 0)  # 绿色
    
    for frame_num in range(total_frames):
        # 创建空白帧
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 计算小车位置（圆形运动）
        t = frame_num / fps  # 时间
        center_x = width // 2
        center_y = height // 2
        radius = 150
        
        car_x = int(center_x + radius * np.cos(t * 0.5))
        car_y = int(center_y + radius * np.sin(t * 0.5))
        
        # 画小车（矩形）
        cv2.rectangle(frame, 
                     (car_x - car_size//2, car_y - car_size//2),
                     (car_x + car_size//2, car_y + car_size//2),
                     car_color, -1)
        
        # 添加一些背景噪点
        for _ in range(50):
            noise_x = np.random.randint(0, width)
            noise_y = np.random.randint(0, height)
            noise_color = tuple(np.random.randint(0, 128, 3).tolist())
            cv2.circle(frame, (noise_x, noise_y), 2, noise_color, -1)
        
        # 添加帧号信息
        cv2.putText(frame, f"Frame: {frame_num}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        out.write(frame)
    
    out.release()
    print("测试视频已创建: test_video.mp4")
    return "test_video.mp4"


def test_tracker(video_path):
    """测试轨迹跟踪器"""
    print(f"测试轨迹跟踪器，视频文件: {video_path}")
    
    try:
        # 创建跟踪器
        tracker = CarTrajectoryTracker(video_path)
        
        # 模拟自动选择（选择中心区域）
        print("自动选择跟踪目标...")
        center_x = tracker.width // 2
        center_y = tracker.height // 2
        size = 60
        tracker.selected_bbox = (center_x - size//2, center_y - size//2, size, size)
        
        # 初始化跟踪器
        if tracker.init_tracker():
            print("跟踪器初始化成功")
            
            # 开始跟踪（不保存视频，加快速度）
            trajectory = tracker.track_car(save_video=False)
            
            if trajectory:
                print(f"跟踪完成，共 {len(trajectory)} 个点")
                
                # 绘制轨迹
                tracker.plot_trajectory("test_trajectory.png", show_plot=False)
                
                # 保存数据
                tracker.save_trajectory_data("test_trajectory_data.json")
                
                # 分析运动
                tracker.analyze_motion()
                
                print("\n测试完成！生成的文件：")
                print("  - test_trajectory.png")
                print("  - test_trajectory_data.json")
                
                return True
            else:
                print("跟踪失败")
                return False
        else:
            print("跟踪器初始化失败")
            return False
    
    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_dependencies():
    """检查依赖包是否正确安装"""
    print("检查依赖包...")
    
    dependencies = {
        'cv2': 'opencv-python',
        'numpy': 'numpy', 
        'matplotlib': 'matplotlib'
    }
    
    missing = []
    
    for module, package in dependencies.items():
        try:
            if module == 'cv2':
                import cv2
                print(f"✓ OpenCV 版本: {cv2.__version__}")
            elif module == 'numpy':
                import numpy as np
                print(f"✓ NumPy 版本: {np.__version__}")
            elif module == 'matplotlib':
                import matplotlib
                print(f"✓ Matplotlib 版本: {matplotlib.__version__}")
        except ImportError:
            missing.append(package)
            print(f"✗ {package} 未安装")
    
    if missing:
        print(f"\n请安装缺失的包:")
        print(f"pip install {' '.join(missing)}")
        return False
    else:
        print("✓ 所有依赖包已正确安装")
        return True


def show_usage_example():
    """显示使用示例"""
    print("\n" + "="*50)
    print("小车轨迹跟踪程序 - 使用示例")
    print("="*50)
    
    print("\n1. 基本使用:")
    print("   python car_trajectory_tracker.py your_video.mp4")
    
    print("\n2. 保存跟踪视频:")
    print("   python car_trajectory_tracker.py your_video.mp4 --save-video")
    
    print("\n3. 指定输出目录:")
    print("   python car_trajectory_tracker.py your_video.mp4 --output-dir results")
    
    print("\n4. 简化版程序:")
    print("   python simple_car_tracker.py your_video.mp4")
    
    print("\n5. 运行测试:")
    print("   python example_usage.py")


def main():
    """主函数"""
    print("小车轨迹跟踪程序 - 示例和测试")
    print("="*40)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 询问用户选择
    while True:
        print("\n请选择操作:")
        print("1. 创建测试视频并测试跟踪")
        print("2. 仅创建测试视频") 
        print("3. 测试现有视频文件")
        print("4. 显示使用示例")
        print("5. 退出")
        
        choice = input("\n请输入选择 (1-5): ").strip()
        
        if choice == '1':
            # 创建测试视频并测试
            video_path = create_test_video()
            if os.path.exists(video_path):
                test_tracker(video_path)
            break
        
        elif choice == '2':
            # 仅创建测试视频
            create_test_video()
            break
        
        elif choice == '3':
            # 测试现有视频
            video_path = input("请输入视频文件路径: ").strip()
            if os.path.exists(video_path):
                test_tracker(video_path)
            else:
                print(f"文件不存在: {video_path}")
            break
        
        elif choice == '4':
            # 显示使用示例
            show_usage_example()
        
        elif choice == '5':
            print("退出程序")
            break
        
        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    main()