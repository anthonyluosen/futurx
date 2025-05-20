#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建基础Futurx conda环境（Python 3.10）
"""

import subprocess
import sys
import platform

# 环境名称和Python版本
ENV_NAME = "futurx"
PYTHON_VERSION = "3.10"

def run_command(command):
    """执行命令并打印输出"""
    print(f"执行: {command}")
    
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # 实时输出
    for stdout_line in iter(process.stdout.readline, ""):
        if stdout_line:
            print(stdout_line.strip())
    
    # 等待命令完成
    process.stdout.close()
    return_code = process.wait()
    
    if return_code != 0:
        error_output = process.stderr.read()
        print(f"命令执行失败: {error_output}")
        return False
    
    return True

def main():
    """主函数"""
    print("======== 创建Futurx环境 (Python 3.10) ========")
    
    # 检查conda是否已安装
    try:
        subprocess.run(
            ["conda", "--version"], 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        print("错误: 未检测到conda。请先安装Anaconda或Miniconda。")
        print("下载地址: https://www.anaconda.com/products/distribution")
        sys.exit(1)
    
    # 创建conda环境
    print(f"正在创建基础conda环境: {ENV_NAME} (Python {PYTHON_VERSION})...")
    if not run_command(f"conda create -y -n {ENV_NAME} python={PYTHON_VERSION}"):
        print("创建环境失败，退出。")
        sys.exit(1)
    
    print("\n======== 环境创建完成 ========")
    print(f"激活环境: conda activate {ENV_NAME}")
    print("===============================")

if __name__ == "__main__":
    main() 