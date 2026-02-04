#!/usr/bin/env python3
"""
虚拟环境设置脚本

这个脚本会自动创建Python虚拟环境并安装所需依赖包
"""

import os
import sys
import subprocess
import platform

def run_command(command, description=""):
    """运行系统命令"""
    if description:
        print(f"正在{description}...")
    
    try:
        if platform.system() == "Windows":
            result = subprocess.run(command, shell=True, check=True, 
                                 capture_output=True, text=True, encoding='utf-8')
        else:
            result = subprocess.run(command, shell=True, check=True, 
                                 capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"错误: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        return False, None

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"错误: 需要Python 3.7或更高版本，当前版本: {version.major}.{version.minor}")
        return False
    print(f"✓ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def create_virtual_environment():
    """创建虚拟环境"""
    venv_path = "venv"
    
    # 检查虚拟环境是否已存在
    if os.path.exists(venv_path):
        print(f"虚拟环境 '{venv_path}' 已存在")
        return True, venv_path
    
    # 创建虚拟环境
    success, output = run_command(f"python -m venv {venv_path}", "创建虚拟环境")
    if success:
        print(f"✓ 虚拟环境已创建: {venv_path}")
        return True, venv_path
    else:
        print("✗ 虚拟环境创建失败")
        return False, None

def get_activation_command(venv_path):
    """获取激活命令"""
    if platform.system() == "Windows":
        return os.path.join(venv_path, "Scripts", "activate.bat")
    else:
        return f"source {os.path.join(venv_path, 'bin', 'activate')}"

def install_dependencies(venv_path):
    """在虚拟环境中安装依赖包"""
    if platform.system() == "Windows":
        pip_command = os.path.join(venv_path, "Scripts", "pip.exe")
        python_command = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        pip_command = os.path.join(venv_path, "bin", "pip")
        python_command = os.path.join(venv_path, "bin", "python")
    
    # 升级pip
    success, output = run_command(f'"{python_command}" -m pip install --upgrade pip', "升级pip")
    if not success:
        print("警告: pip升级失败，继续安装依赖包...")
    
    # 检查requirements.txt是否存在
    if os.path.exists("requirements.txt"):
        success, output = run_command(f'"{pip_command}" install -r requirements.txt', "安装依赖包")
        if success:
            print("✓ 依赖包安装完成")
            return True
        else:
            print("✗ 依赖包安装失败")
            return False
    else:
        # 手动安装基本依赖
        packages = ["opencv-python", "numpy", "matplotlib"]
        for package in packages:
            success, output = run_command(f'"{pip_command}" install {package}', f"安装 {package}")
            if success:
                print(f"✓ {package} 安装完成")
            else:
                print(f"✗ {package} 安装失败")
                return False
        return True

def create_activation_scripts(venv_path):
    """创建激活脚本"""
    # Windows批处理文件
    if platform.system() == "Windows":
        activate_script = """@echo off
echo 激活小车轨迹跟踪项目虚拟环境...
call venv\\Scripts\\activate.bat
echo.
echo ========================================
echo 虚拟环境已激活！
echo.
echo 现在您可以运行：
echo   python car_trajectory_tracker.py your_video.mp4
echo   python simple_car_tracker.py your_video.mp4  
echo   python example_usage.py
echo.
echo 退出虚拟环境请输入: deactivate
echo ========================================
echo.
cmd /k
"""
        with open("activate_env.bat", "w", encoding="utf-8") as f:
            f.write(activate_script)
        print("✓ 已创建 activate_env.bat 激活脚本")
    
    # 跨平台脚本
    activate_script_sh = f"""#!/bin/bash
echo "激活小车轨迹跟踪项目虚拟环境..."
source {venv_path}/bin/activate
echo ""
echo "========================================"
echo "虚拟环境已激活！"
echo ""
echo "现在您可以运行："
echo "  python car_trajectory_tracker.py your_video.mp4"
echo "  python simple_car_tracker.py your_video.mp4"
echo "  python example_usage.py"
echo ""
echo "退出虚拟环境请输入: deactivate"
echo "========================================"
echo ""
exec "$SHELL"
"""
    with open("activate_env.sh", "w", encoding="utf-8") as f:
        f.write(activate_script_sh)
    
    # 给shell脚本执行权限
    if platform.system() != "Windows":
        run_command("chmod +x activate_env.sh")
    
    print("✓ 已创建 activate_env.sh 激活脚本")

def main():
    """主函数"""
    print("=" * 50)
    print("小车轨迹跟踪项目 - 虚拟环境设置")
    print("=" * 50)
    print()
    
    # 检查Python版本
    if not check_python_version():
        return False
    
    # 创建虚拟环境
    success, venv_path = create_virtual_environment()
    if not success:
        return False
    
    # 安装依赖包
    if not install_dependencies(venv_path):
        return False
    
    # 创建激活脚本
    create_activation_scripts(venv_path)
    
    print()
    print("=" * 50)
    print("✓ 虚拟环境设置完成！")
    print("=" * 50)
    print()
    print("接下来的步骤：")
    
    if platform.system() == "Windows":
        print("1. 双击 activate_env.bat 激活虚拟环境")
        print("   或者在命令行运行: activate_env.bat")
        print()
        print("2. 手动激活方式:")
        print("   venv\\Scripts\\activate")
    else:
        print("1. 运行激活脚本:")
        print("   ./activate_env.sh")
        print()
        print("2. 手动激活方式:")
        print(f"   source {venv_path}/bin/activate")
    
    print()
    print("3. 激活后运行程序:")
    print("   python car_trajectory_tracker.py your_video.mp4")
    print("   python simple_car_tracker.py your_video.mp4")
    print("   python example_usage.py")
    print()
    print("4. 退出虚拟环境:")
    print("   deactivate")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print()
        input("按回车键退出...")
        sys.exit(1)