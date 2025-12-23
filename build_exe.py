"""打包脚本：生成单文件 exe（包含前端静态资源，不打包三份 JSON 数据）。

用法（在项目根目录）：
    python build_exe.py

要求：
- 已创建虚拟环境，若未安装 pyinstaller，脚本会自动安装
- 前端已构建：frontend/dist 存在（否则脚本会报错）
- 三个数据文件 inference_history.json / rules.json / users.json 不会被打包，按需求外置
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
FRONTEND_DIST = ROOT / "frontend" / "dist"
SPEC_FILE = ROOT / "rgzn.spec"


def ensure_frontend_built() -> None:
    if not FRONTEND_DIST.exists():
        raise FileNotFoundError(
            f"前端构建目录不存在: {FRONTEND_DIST}\n"
            "请先在 frontend 目录执行 `pnpm build` 再运行本脚本。"
        )


def clean_old_builds() -> None:
    for path in [ROOT / "build", ROOT / "dist", SPEC_FILE]:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()


def ensure_pyinstaller(python_cmd: list[str]) -> None:
    """如果未安装 PyInstaller，则自动安装。"""
    if importlib.util.find_spec("PyInstaller") is not None:
        return

    print("未检测到 PyInstaller，正在安装...")
    install_cmd = python_cmd + ["-m", "pip", "install", "pyinstaller"]
    subprocess.run(install_cmd, check=True)


def build_exe() -> None:
    python_cmd = [str(VENV_PYTHON)] if VENV_PYTHON.exists() else [sys.executable]
    print(f"使用 Python: {python_cmd[0]}")

    ensure_pyinstaller(python_cmd)

    data_sep = ";"  # Windows 下 PyInstaller --add-data 分隔符
    add_data = f"{FRONTEND_DIST}{data_sep}frontend/dist"

    cmd = python_cmd + [
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name",
        "rgzn",
        "--add-data",
        add_data,
        # 需要外置的 JSON 不打包，保持默认即可
        str(ROOT / "main.py"),
    ]

    print("运行命令:\n", " ".join(cmd))
    subprocess.run(cmd, check=True)

    print("\n打包完成，生成文件位于 dist/rgzn.exe")
    print("提示：运行时将 inference_history.json、rules.json、users.json 放在 exe 同目录以便读取/写回。")


def main() -> None:
    ensure_frontend_built()
    clean_old_builds()
    build_exe()


if __name__ == "__main__":
    main()
