# 基于产生式知识表示的专家系统

使用 C++ 推理引擎 + Python GUI/Web 的专家系统，支持正向推理、反向推理、知识库管理等功能。

## 功能特性

- **正向推理**：从已知事实出发，逐步应用规则推导出新的结论
- **反向推理**：从目标结论出发，反向寻找需要满足的条件
- **冲突消解**：当多条规则可应用时，选择优先级最高的规则
- **推理可视化**：通过图形展示推理过程和路径
- **知识库管理**：支持规则的增删改查
- **历史记录**：保存每次推理的结果，方便回顾（Web版）
- **用户认证**：支持用户注册登录，管理员权限控制（Web版）

## 运行方式

### 1. 桌面 GUI 版本（PyQt6）

```bash
python expert_system_gui.py
```

GUI 中包含 "Web服务器" 标签页，可以在 GUI 内启动 Web 服务。

### 2. 仅 Web 服务器模式

```bash
# 仅启动 Web 服务器（无 GUI）
python expert_system_gui.py --web

# 指定端口
python expert_system_gui.py --web --port 8080
```

### 3. 打包后的 EXE

```bash
# 正常启动 GUI
expert_system_gui.exe

# 仅启动 Web 服务器
expert_system_gui.exe --web --port 5000
```

### 首次使用 Web 版

```bash
# 1. 安装后端依赖
pip install flask flask-cors

# 2. 构建前端
cd web_frontend
npm install
npm run build
cd ..
```

访问 http://localhost:5000，默认管理员账号：`admin` / `admin123`

---

## C++ 推理引擎模块

使用 [nanobind](https://nanobind.readthedocs.io/) + [scikit-build-core](https://scikit-build-core.readthedocs.io/) 将 C++ `Rule_reasoner` 推理引擎编译为可直接在 Python 中导入的扩展模块。

## 开发环境要求

- Windows 10/11（或任意支持的桌面操作系统）
- Python 3.9 及以上版本（64 位）
- Microsoft C++ Build Tools 或 Visual Studio（用于提供 `cl.exe`）
- `pip` 可联网安装构建依赖

> 如果你偏好 MinGW-w64/GCC，也可以在激活相应环境后执行相同的命令，只需保证 `python` 使用的编译器与 Python ABI 兼容即可。

## 安装依赖

```powershell
python -m pip install --upgrade pip
python -m pip install --upgrade scikit-build-core nanobind
```

## 编译 / 安装

在项目根目录执行：

```powershell
# 构建并生成可导入扩展（轮子在 dist/）
python -m pip install .

# 或开发模式
python -m pip install -e .
```

构建过程中 CMake 会在 `cpp_py/out` 下生成对应的 `.pyd` 和 `.pyi`，并复制到安装包（包名 `rule`）。

## Python 端用法示例

```python
from rule_reasoner import RuleReasoner

rr = RuleReasoner()
rr.add_rule(["会飞", "下蛋"], "是鸟")
rr.add_rule(["是鸟"], "是动物")
rr.add_known(["会飞", "下蛋"])

for result, path in rr.find_with_names():
    print("推理结论:", result, "路径:", path)
```

`add_rule` / `add_known` 等均支持 Python 的任意可迭代对象（列表、元组等），推理结果会返回形如 `(名字, [规则ID...])` 的列表。

## 常见问题

- **无法找到编译器**：请先安装 Visual Studio Build Tools，并在“x64 Native Tools Command Prompt”中运行上述命令，或将 `cl.exe` 所在目录加入环境变量。
- **pybind11 未安装**：依赖在 `pyproject.toml` 中已声明，确保 `pip install .` 会自动拉取；若使用 `setup.py build_ext --inplace`，需提前手动安装（见上文）。
- **重新编译**：修改 C++ 源码后，重新执行 `python setup.py build_ext --inplace` 即可覆盖旧的 `.pyd` 文件。
