@echo off
echo ========================================
echo 小车轨迹跟踪项目 - 环境设置
echo ========================================
echo.

echo 正在检查Python安装...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.7或更高版本
    pause
    exit /b 1
)

echo 正在运行环境设置脚本...
echo.
python setup_env.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo 安装完成！现在可以使用以下方式之一激活环境:
    echo.
    echo 方式1: 双击 activate_env.bat
    echo 方式2: 在命令行运行 activate_env.bat
    echo 方式3: 手动运行 venv\Scripts\activate
    echo ========================================
) else (
    echo.
    echo 安装过程中出现错误，请检查错误信息
)

echo.
pause