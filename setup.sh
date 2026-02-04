#!/bin/bash

echo "========================================"
echo "小车轨迹跟踪项目 - 环境设置"
echo "========================================"
echo

echo "正在检查Python安装..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "错误: 未找到Python，请先安装Python 3.7或更高版本"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "正在运行环境设置脚本..."
echo
$PYTHON_CMD setup_env.py

if [ $? -eq 0 ]; then
    echo
    echo "========================================"
    echo "安装完成！现在可以使用以下方式激活环境:"
    echo
    echo "方式1: ./activate_env.sh"
    echo "方式2: source venv/bin/activate"
    echo "========================================"
else
    echo
    echo "安装过程中出现错误，请检查错误信息"
fi

echo
read -p "按回车键退出..."