# 快速开始指南

## 🚀 10秒快速设置

### 有conda的用户（推荐）
```bash
conda env create -f environment.yml
conda activate car-tracker
```

**GUI版本（推荐）**
```bash
python car_tracker_gui.py
```

**命令行版本**
```bash
python car_trajectory_tracker.py your_video.mp4
```

### 没有conda的用户
```bash
pip install opencv-python numpy matplotlib
python car_tracker_gui.py
```

## 📁 重要文件说明

| 文件名 | 作用 | 使用方式 |
|--------|------|----------|
| `setup.bat/.sh` | 一键安装环境 | 双击(Windows)或`./setup.sh`(Linux/Mac) |
| `activate_env.bat/.sh` | 激活虚拟环境 | 双击(Windows)或`./activate_env.sh`(Linux/Mac) |
| `car_trajectory_tracker.py` | 主程序(完整版) | `python car_trajectory_tracker.py video.mp4` |
| `simple_car_tracker.py` | 简化版程序 | `python simple_car_tracker.py video.mp4` |
| `example_usage.py` | 测试和示例 | `python example_usage.py` |

## 🎯 第一次使用建议

1. **先运行测试**：`python example_usage.py` - 创建测试视频并验证程序
2. **使用简化版**：`python simple_car_tracker.py video.mp4` - 功能简单，易于理解
3. **使用完整版**：`python car_trajectory_tracker.py video.mp4` - 功能强大，分析详细

## ⚠️ 重要提醒

- **必须在虚拟环境中运行程序**
- Windows用户确保双击 `activate_env.bat` 后看到 `(venv)` 前缀
- Linux/Mac用户确保运行 `./activate_env.sh` 后看到 `(venv)` 前缀
- 程序运行完毕后可以输入 `deactivate` 退出虚拟环境

## 🔧 手动操作（高级用户）

如果自动脚本有问题，可以手动执行：

```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. 安装依赖
pip install opencv-python numpy matplotlib

# 4. 运行程序
python car_trajectory_tracker.py your_video.mp4
```

---

有问题？查看完整说明：[README.md](README.md)