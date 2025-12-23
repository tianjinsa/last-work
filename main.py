"""
基于产生式知识表示的专家系统 - 主入口

运行方式:
  python main.py          # 启动 GUI
  python main.py --web    # 仅启动 Web 服务器
  python main.py --web --port 8080  # 指定端口
"""

import argparse
import sys


def run_gui():
    """启动 GUI 应用"""
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import QApplication

    from src.gui import ExpertSystemGUI

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))

    window = ExpertSystemGUI()
    window.show()

    sys.exit(app.exec())


def run_web(host: str, port: int):
    """启动 Web 服务器"""
    try:
        from src.web.server import run_standalone

        run_standalone(host=host, port=port)
    except ImportError as e:
        print(f"错误: 无法导入Web服务器模块 - {e}")
        print("请确保已安装 flask 和 flask-cors:")
        print("  uv sync")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="基于产生式知识表示的专家系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py              # 启动 GUI
  python main.py --web        # 仅启动 Web 服务器
  python main.py --web --port 8080  # 指定端口
        """,
    )
    parser.add_argument(
        "--web", action="store_true", help="仅启动 Web 服务器（不显示 GUI）"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Web 服务器监听地址（默认: 0.0.0.0）"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Web 服务器端口（默认: 5000）"
    )

    args = parser.parse_args()

    if args.web:
        run_web(host=args.host, port=args.port)
    else:
        run_gui()


if __name__ == "__main__":
    main()
