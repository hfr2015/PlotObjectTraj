# 小车轨迹跟踪程序

这个程序可以从视频中选择并跟踪小车，绘制其运动轨迹。支持多种跟踪算法和详细的轨迹分析。

## 功能特点

### 🎯 核心功能
- **视频加载**: 支持常见视频格式 (MP4, AVI, MOV等)
- **目标选择**: 鼠标框选要跟踪的小车
- **实时跟踪**: 使用OpenCV的CSRT跟踪算法
- **轨迹绘制**: 生成高质量的轨迹图和运动分析
- **数据导出**: 保存轨迹数据为JSON格式

### 📊 分析功能
- 运动轨迹可视化
- 速度和加速度分析
- 时间-距离关系图
- 运动统计信息

## 安装要求

### Python版本
- Python 3.7 或更高版本

### 快速安装（推荐）

**使用conda（推荐）**
```bash
conda env create -f environment.yml
conda activate car-tracker
```

**使用pip**
```bash
pip install opencv-python numpy matplotlib
```

**或使用requirements.txt**
```bash
pip install -r requirements.txt
```

## 使用方法

### ⚡ 超简单使用

**GUI版本（最推荐）**
```bash
conda env create -f environment.yml
conda activate car-tracker
python car_tracker_gui.py
```

**命令行版本**
```bash
conda env create -f environment.yml  
conda activate car-tracker
python car_trajectory_tracker.py your_video.mp4
```

**没有conda**
```bash
pip install opencv-python numpy matplotlib
python car_tracker_gui.py
```

### 详细使用方法

### GUI版本（推荐新手）

启动图形界面：
```bash
python car_tracker_gui.py
```

**操作步骤：**
1. **选择视频**：点击"选择视频"按钮，选择要分析的视频文件
2. **选择目标**：点击"选择跟踪目标"，在弹出窗口中框选小车
3. **开始跟踪**：点击"开始跟踪"，程序自动跟踪并显示进度
4. **查看结果**：跟踪完成后点击"查看轨迹"查看图形，"保存数据"保存结果

**GUI特点：**
- ✅ 直观的图形界面，无需命令行
- ✅ 实时显示跟踪进度和统计信息  
- ✅ 内置轨迹可视化窗口
- ✅ 一键保存轨迹图片和数据
- ✅ 详细的操作日志

### 方法1：完整版程序（推荐）

```bash
python car_trajectory_tracker.py <视频文件路径> [选项]
```

**参数说明：**
- `<视频文件路径>`: 必需，视频文件的路径
- `--save-video`: 可选，保存跟踪过程的视频
- `--output-dir`: 可选，指定输出目录（默认当前目录）

**示例：**
```bash
# 基本使用
python car_trajectory_tracker.py my_video.mp4

# 保存跟踪视频到指定目录
python car_trajectory_tracker.py my_video.mp4 --save-video --output-dir ./results
```

### 方法2：简化版程序（适合初学者）

```bash
python simple_car_tracker.py <视频文件>
```

**示例：**
```bash
python simple_car_tracker.py my_video.mp4
```

## 操作步骤

### 1. 启动程序
运行命令后，程序会显示视频信息（分辨率、帧率等）

### 2. 选择目标
- 程序会弹出视频窗口显示第一帧
- 用鼠标**点击并拖拽**框选要跟踪的小车
- 确保选择区域完整包含小车
- 按**空格键**确认选择，按**ESC**取消

### 3. 跟踪过程
- 程序开始自动跟踪选中的小车
- 实时显示跟踪窗口：
  - 绿色框：跟踪的边界框
  - 红色点：小车中心点
  - 蓝色线：已走过的轨迹
- 按**ESC**可提前停止跟踪

### 4. 查看结果
跟踪完成后自动生成：
- **轨迹图**: `car_trajectory.png` - 可视化轨迹图
- **数据文件**: `car_trajectory_data.json` - 原始轨迹数据
- **分析报告**: 控制台输出运动统计信息
- **跟踪视频** (可选): `tracked_output.mp4`

## 输出文件说明

### 轨迹图 (PNG格式)
- 左图：2D轨迹图，显示小车运动路径
  - 绿点：起点
  - 红点：终点  
  - 红色箭头：运动方向
- 右图：时间-距离关系图

### 数据文件 (JSON格式)
```json
{
  "video_info": {
    "path": "视频路径",
    "width": "视频宽度",
    "height": "视频高度", 
    "fps": "帧率",
    "total_frames": "总帧数"
  },
  "trajectory": [
    [x坐标, y坐标, 帧号],
    ...
  ],
  "selected_bbox": [x, y, 宽度, 高度]
}
```

### 运动分析信息
程序会在控制台输出：
- 总轨迹点数
- 总运动时间
- 总运动距离  
- 平均/最大/最小速度
- 最大/最小加速度

## 技术细节

### 跟踪算法
程序使用OpenCV的**CSRT (Channel and Spatial Reliability Tracking)** 算法：
- 高精度跟踪
- 对遮挡和形变有较好鲁棒性
- 适合跟踪小车等刚性目标

### 坐标系统
- 使用图像像素坐标系
- 原点(0,0)在图像左上角
- X轴向右，Y轴向下
- 轨迹图中Y轴已反转，符合常规习惯

## 常见问题

### Q: 跟踪效果不好怎么办？
**A**: 
- 确保选择区域紧贴小车边界
- 避免选择过大或过小的区域
- 选择小车特征明显的帧进行初始化
- 确保视频清晰度足够

### Q: 程序运行很慢？
**A**:
- 降低视频分辨率
- 跳帧处理（修改代码中的帧间隔）
- 使用性能更好的计算机

### Q: 跟踪中途丢失目标？
**A**:
- 程序会自动检测跟踪失败
- 连续丢失10帧后自动停止
- 可调整代码中的`max_lost_frames`参数

### Q: 支持哪些视频格式？
**A**:
支持OpenCV可读取的所有格式：
- MP4, AVI, MOV, MKV
- WMV, FLV, WEBM等

### Q: 如何提高跟踪精度？
**A**:
- 选择高对比度、特征明显的小车
- 确保光照条件良好
- 避免有严重遮挡的场景

## 扩展功能

### 自定义跟踪器
可修改代码使用其他跟踪算法：
```python
# 替换 cv2.TrackerCSRT_create() 为:
tracker = cv2.TrackerKCF_create()    # KCF跟踪器
tracker = cv2.TrackerMOSSE_create()  # MOSSE跟踪器
```

### 多目标跟踪
程序架构支持扩展为多目标跟踪，需要：
1. 修改目标选择逻辑
2. 使用多个跟踪器实例
3. 管理多条轨迹数据

## 版本信息

- **版本**: 1.0.0
- **作者**: Cop, Rui Gao  
- **更新日期**: 2026-02-01
- **Python要求**: ≥3.7
- **主要依赖**: OpenCV ≥4.5.0

## 许可证

本程序仅供学习和研究使用。

## 技术支持

如遇问题，请检查：
1. Python和依赖包版本是否符合要求
2. 视频文件是否完整且格式支持
3. 系统内存是否充足

---


**享受轨迹跟踪的乐趣！** 🚗📈
