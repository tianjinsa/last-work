# 基于产生式知识表示的专家系统

纯 Python 推理引擎 + PyQt6 GUI + Vue3 Web 前端的专家系统，支持正向推理、反向推理、知识库管理等功能。

## 功能特性

- 正向推理：从已知事实出发，逐步应用规则推导出新的结论
- 反向推理：从目标结论出发，反向寻找需要满足的条件
- 推理可视化：通过图形展示推理过程和路径
- 知识库管理：支持规则的增删改查
- 用户认证：支持用户注册登录，管理员权限控制（Web 版）
- 历史记录：保存每次推理结果，方便回顾（Web 版）

## 安装

```bash
uv sync
```

## 运行

```bash
# 启动 GUI
uv run python main.py

# 仅启动 Web 服务器
uv run python main.py --web

# 指定端口
uv run python main.py --web --port 8080
```

## 首次使用 Web 版

```bash
cd frontend
pnpm install
pnpm build
cd ..
```

访问 http://localhost:5000，默认管理员账号：`admin` / `admin123`

## 项目结构

```
├── main.py                 # 主入口
├── src/
│   ├── core/               # 推理引擎
│   │   └── reasoner.py     # RuleReasoner 类
│   ├── data/               # 数据存储
│   │   ├── storage.py      # DataStorage 类
│   │   └── constants.py    # 默认规则
│   ├── gui/                # GUI 组件
│   │   ├── dialogs.py      # 对话框组件
│   │   ├── graph_widget.py # 推理图可视化
│   │   └── main_window.py  # 主窗口
│   └── web/                # Web 服务器
│       └── server.py       # Flask API
├── frontend/               # Vue3 前端
├── pyproject.toml          # 项目配置
└── rules.json              # 规则库
```

## 推理引擎 API

```python
from src.core import RuleReasoner

rr = RuleReasoner()
rr.reset([
    (["会飞", "下蛋"], "鸟"),
    (["鸟"], "动物")
])
rr.add_known(["会飞", "下蛋"])

# 正向推理
conclusions, path = rr.find()
print(conclusions)  # ['动物']

# 反向推理
status, data, path = rr.step_backward("动物")
# status: 0=成功, 1=失败, 2=需要询问用户
```

## 技术栈

- 后端：Python 3.12+, Flask, PyQt6
- 前端：Vue 3, Vite, Element Plus, vis-network
- 包管理：uv (Python), pnpm (Node.js)
