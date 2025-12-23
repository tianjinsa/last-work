"""
打包脚本 - 将专家系统打包为单个 EXE
包含前端静态文件和所有依赖
"""

import os
import subprocess
import sys


def main():
    # 确保在正确的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("=" * 50)
    print("专家系统打包脚本")
    print("=" * 50)
    
    # 1. 检查前端是否已构建
    frontend_dist = os.path.join(script_dir, "web_frontend", "dist")
    if not os.path.exists(frontend_dist):
        print("\n[!] 前端未构建，正在构建...")
        frontend_dir = os.path.join(script_dir, "web_frontend")
        result = subprocess.run(["pnpm", "build"], cwd=frontend_dir, shell=True)
        if result.returncode != 0:
            print("[错误] 前端构建失败！")
            sys.exit(1)
        print("[✓] 前端构建完成")
    else:
        print("[✓] 检测到前端已构建")
    
    # 2. 检查 rules.json
    rules_file = os.path.join(script_dir, "rules.json")
    if not os.path.exists(rules_file):
        print("[!] 警告: rules.json 不存在，将使用默认规则")
    
    # 3. 运行 PyInstaller
    print("\n[*] 正在打包 EXE...")
    
    # Windows 使用分号，Linux/Mac 使用冒号
    separator = ";" if sys.platform == "win32" else ":"
    
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name", "ExpertSystem",
        # 添加前端静态文件
        "--add-data", f"web_frontend/dist{separator}web_frontend/dist",
        # 添加规则文件（可选，运行时会自动创建）
        # "--add-data", f"rules.json{separator}.",
        # 主程序
        "expert_system_gui.py"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("[✓] 打包成功！")
        print(f"    输出文件: {os.path.join(script_dir, 'dist', 'ExpertSystem.exe')}")
        print("\n使用方法:")
        print("  - 双击运行: 启动完整GUI")
        print("  - 命令行运行: ExpertSystem.exe --web --port 5000")
        print("    (仅启动Web服务器，不显示GUI)")
        print("=" * 50)
    else:
        print("\n[错误] 打包失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()
