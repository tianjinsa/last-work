"""
ptyhon>=3.12

基于产生式知识表示的专家系统 - PyQt6 GUI
功能：
1. 正向推理和反向推理
2. 提示/允许用户补充事实
3. 知识库增删改
4. 冲突消解
5. 结论解释（推理路径图）
6. 综合数据库动态展示
7. 启动Web服务器

命令行参数：
  --web       仅启动Web服务器（不显示GUI）
  --port PORT Web服务器端口（默认5000）
"""

import argparse
import json
import os
import sys

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from Rule_reasoner import Rule_reasoner


class FactSelectionDialog(QDialog):
    """事实选择对话框"""

    def __init__(
        self,
        all_facts: list[str],
        user_facts: list[str],
        intermediate_facts: list[str] | None = None,
    ):
        super().__init__()
        self.setWindowTitle("选择事实")
        self.resize(700, 500)

        self.selected_facts = set(user_facts)
        self.stop_facts = set(intermediate_facts) if intermediate_facts else set()
        self.all_facts = set(all_facts) - self.stop_facts - self.selected_facts

        main_layout = QVBoxLayout(self)

        # Content area
        content_layout = QHBoxLayout()

        # 左边: 可选事实
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("可选事实 (点击添加):"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索事实...")
        self.search_input.textChanged.connect(self.filter_facts)
        left_layout.addWidget(self.search_input)

        self.available_list = QListWidget()
        self.available_list.itemClicked.connect(self.add_fact)

        left_layout.addWidget(self.available_list)

        content_layout.addWidget(left_widget)

        # 右边: 已选事实
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("已选事实 (点击移除):"))

        self.selected_list = QListWidget()
        self.selected_list.itemClicked.connect(self.remove_fact)

        right_layout.addWidget(self.selected_list)

        content_layout.addWidget(right_widget)

        main_layout.addLayout(content_layout)

        # Bottom buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.refresh_lists()

    def filter_facts(self, text: str):
        self.refresh_lists()

    def refresh_lists(self):
        self.available_list.clear()
        self.selected_list.clear()

        search_text = self.search_input.text().lower()

        self.available_list.addItems(
            [
                fact
                for fact in sorted(list(self.all_facts))
                if search_text in fact.lower()
            ]
        )

        for fact in sorted(list(self.stop_facts)):
            item = QListWidgetItem("*" + fact)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            font = item.font()
            font.setItalic(True)
            item.setFont(font)
            item.setToolTip("中间事实，无法移除")
            self.selected_list.addItem(item)
        self.selected_list.addItems(sorted(list(self.selected_facts)))

    def add_fact(self, item):
        fact = item.text()
        self.selected_facts.add(fact)
        self.all_facts.discard(fact)
        self.refresh_lists()

    def remove_fact(self, item):
        fact = item.text()
        if fact.startswith("*"):
            return
        self.all_facts.add(fact)
        self.selected_facts.discard(fact)
        self.refresh_lists()

    def get_selected_facts(self) -> list[str]:
        return list(self.selected_facts)


class RuleEditDialog(QDialog):
    """规则编辑对话框"""

    def __init__(
        self, parent=None, premises: list[str] | None = None, conclusion: str = ""
    ):
        super().__init__(parent)
        self.setWindowTitle("编辑规则")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.premises_edit = QLineEdit()
        self.premises_edit.setPlaceholderText("用逗号分隔多个前提，如：会飞,下蛋")
        if premises:
            self.premises_edit.setText(",".join(premises))

        self.conclusion_edit = QLineEdit()
        self.conclusion_edit.setPlaceholderText("结论")
        self.conclusion_edit.setText(conclusion)

        layout.addRow("前提条件:", self.premises_edit)
        layout.addRow("结论:", self.conclusion_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_rule(self) -> tuple[list[str], str]:
        premises = [
            p.strip() for p in self.premises_edit.text().split(",") if p.strip()
        ]
        conclusion = self.conclusion_edit.text().strip()
        return premises, conclusion


class FactQueryDialog(QDialog):
    """事实询问对话框"""

    def __init__(self, facts: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("需要确认事实")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("推理过程需要以下事实，请勾选已知为真的事实："))

        self.checkboxes: list[QCheckBox] = []
        for fact in facts:
            cb = QCheckBox(fact)
            cb.setChecked(True)
            self.checkboxes.append(cb)
            layout.addWidget(cb)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确认选中为真")  # pyright: ignore[reportOptionalMemberAccess]
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("全部为假/取消")  # pyright: ignore[reportOptionalMemberAccess]

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_true_facts(self) -> list[str]:
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]


class InferenceGraphWidget(QWidget):
    """推理路径图显示组件 (使用 Mermaid) - 增强版"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # 1. 图形显示区域
        self.web_view = QWebEngineView()
        # 设置背景透明，由HTML控制颜色
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)  # pyright: ignore[reportOptionalMemberAccess]
        layout.addWidget(self.web_view, stretch=4)

        # 2. 控制区域
        controls_layout = QHBoxLayout()

        self.prev_btn = QPushButton("上一步")
        self.prev_btn.clicked.connect(self.go_prev)
        controls_layout.addWidget(self.prev_btn)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self.on_slider_changed)
        controls_layout.addWidget(self.slider)

        self.next_btn = QPushButton("下一步")
        self.next_btn.clicked.connect(self.go_next)
        controls_layout.addWidget(self.next_btn)

        self.step_label = QLabel("步骤: 0/0")
        controls_layout.addWidget(self.step_label)

        layout.addLayout(controls_layout)

        # 3. 信息展示区域 (水平布局)
        info_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 推理解释
        exp_group = QGroupBox("推理解释")
        exp_layout = QVBoxLayout(exp_group)
        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        exp_layout.addWidget(self.explanation_text)
        info_splitter.addWidget(exp_group)

        # 综合数据库 (当前已知事实) - 密铺显示
        db_group = QGroupBox("综合数据库")
        db_layout = QVBoxLayout(db_group)
        self.database_list = QListWidget()
        self.database_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.database_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.database_list.setSpacing(4)
        self.database_list.setMovement(QListWidget.Movement.Static)
        db_layout.addWidget(self.database_list)
        info_splitter.addWidget(db_group)

        # 推理结果
        res_group = QGroupBox("推理结果")
        res_layout = QVBoxLayout(res_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        res_layout.addWidget(self.result_text)
        info_splitter.addWidget(res_group)

        layout.addWidget(info_splitter, stretch=2)

        # 内部状态
        self.path: list[int] = []
        self.all_rules: list[tuple[list[str], str]] = []
        self.initial_facts: list[str] = []
        self.final_conclusion: str = ""
        self.current_step = 0
        self.step_states = []  # 预计算每一步的状态
        self.web_ready = False
        self._pending_mermaid: dict | None = None

        # 初始化 WebEngine，仅加载一次模板
        self._init_web_view()

    def _init_web_view(self):
        template = (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            '  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>\n'
            "  <style>\n"
            "    body { margin: 0; padding: 0; background-color: #1e1e1e; height: 100vh; overflow: hidden; }\n"
            "    #mynetwork { width: 100%; height: 100%; }\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            "  <div id='mynetwork'></div>\n"
            "  <script>\n"
            "    var network = null;\n"
            "    window.updateGraph = function(graphData) {\n"
            "      var container = document.getElementById('mynetwork');\n"
            "      var data = {\n"
            "        nodes: new vis.DataSet(graphData.nodes),\n"
            "        edges: new vis.DataSet(graphData.edges)\n"
            "      };\n"
            "      var options = {\n"
            "        nodes: {\n"
            "          shape: 'box',\n"
            "          font: { color: '#ffffff', size: 16, face: 'Microsoft YaHei' },\n"
            "          borderWidth: 1,\n"
            "          shadow: true,\n"
            "          margin: 10,\n"
            "widthConstraint: {\n"
            "maximum: 100\n"
            "}\n"
            "        },\n"
            "        edges: {\n"
            "          arrows: 'to',\n"
            "          color: { color: '#decdc3', highlight: '#ffffff' },\n"
            "          smooth: { type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.5 }\n"
            "        },\n"
            "        layout: {\n"
            "          hierarchical: {\n"
            "            direction: 'DU',\n"
            "            sortMethod: 'directed',\n"
            "            levelSeparation: 120,\n"
            "            nodeSpacing: 150,\n"
            "            blockShifting: true,\n"
            "            edgeMinimization: true,\n"
            "            parentCentralization: true\n"
            "          }\n"
            "        },\n"
            "        physics: {\n"
            "          enabled: true,\n"
            "          hierarchicalRepulsion: {\n"
            "            centralGravity: 0.3,\n"
            "            springLength: 120,\n"
            "            springConstant: 1,\n"
            "            nodeDistance: 120,\n"
            "            damping: 1\n"
            "          },\n"
            "          solver: 'hierarchicalRepulsion'\n"
            "        }\n"
            "      };\n"
            "      if (network !== null) {\n"
            "        network.destroy();\n"
            "        network = null;\n"
            "      }\n"
            "      network = new vis.Network(container, data, options);\n"
            "      network.on('dragStart', function (params) {\n"
            "        network.setOptions({ physics: { enabled: false } });\n"
            "      });\n"
            "      network.on('dragEnd', function (params) {\n"
            "        network.setOptions({ physics: { enabled: true } });\n"
            "      });\n"
            "    };\n"
            "  </script>\n"
            "</body>\n"
            "</html>"
        )

        def on_load_finished(_ok: bool):
            self.web_ready = True
            if self._pending_mermaid is not None:
                self._render_graph(self._pending_mermaid)
                self._pending_mermaid = None

        self.web_view.loadFinished.connect(on_load_finished)
        self.web_view.setHtml(template)

    def _render_graph(self, graph_data: dict):
        if self.web_ready:
            js = f"window.updateGraph({json.dumps(graph_data)})"
            page = self.web_view.page()
            if page is not None:
                page.runJavaScript(js)
        else:
            self._pending_mermaid = graph_data  # Reuse variable for pending data

    def set_data(
        self,
        path: list[int],
        all_rules: list[tuple[list[str], str]],
        initial_facts: list[str],
        conclusion: str,
        result_msg: str,
    ):
        """设置推理数据并初始化视图"""
        print("设置推理图数据:", path, initial_facts, conclusion)
        self.path = path
        self.all_rules = all_rules
        self.initial_facts = list(initial_facts)
        self.final_conclusion = conclusion

        self.result_text.setText(result_msg)

        # 预计算每一步的状态
        self.precalculate_steps()

        # 设置滑块范围
        total_steps = len(path)
        self.slider.setRange(0, total_steps)
        self.slider.setValue(total_steps)  # 默认显示最后一步

        self.update_view(total_steps)

    def precalculate_steps(self):
        """预计算每一步的事实集合和解释文本，提高滑动时的响应速度"""
        self.step_states = []
        current_facts = set(self.initial_facts)

        # 步骤 0: 初始状态
        self.step_states.append(
            {
                "facts": current_facts.copy(),
                "explanation": "初始状态，仅包含已知事实。",
                "path_ids": [],
            }
        )

        explanation_lines = []
        for i, rule_id in enumerate(self.path):
            if rule_id < len(self.all_rules):
                pres, ans = self.all_rules[rule_id]
                # 模拟推理：如果前提满足，加入结论
                # 注意：这里假设C++返回的路径是有效的，即前提一定满足
                if all(p in current_facts for p in pres):
                    current_facts.add(ans)
                    explanation_lines.append(
                        f"步骤{i + 1}: 由 {' + '.join(pres)} → {ans} (规则{rule_id})"
                    )

            self.step_states.append(
                {
                    "facts": current_facts.copy(),
                    "explanation": "\n".join(explanation_lines),
                    "path_ids": self.path[: i + 1],
                }
            )

    def go_prev(self):
        val = self.slider.value()
        if val > 0:
            self.slider.setValue(val - 1)

    def go_next(self):
        val = self.slider.value()
        if val < self.slider.maximum():
            self.slider.setValue(val + 1)

    def on_slider_changed(self, value):
        self.update_view(value)

    def update_view(self, step):
        """更新视图到指定步骤"""
        self.current_step = step
        self.step_label.setText(f"步骤: {step}/{len(self.path)}")

        if step < len(self.step_states):
            state = self.step_states[step]

            # 1. 更新综合数据库显示
            self.database_list.clear()
            for fact in sorted(list(state["facts"])):
                item = QListWidgetItem(fact)
                item.setSizeHint(item.sizeHint())
                self.database_list.addItem(item)

            # 2. 更新解释文本
            self.explanation_text.setText(state["explanation"])

            # 3. 绘制图
            self.draw_graph(state["path_ids"], state["facts"])

    def draw_graph(self, current_path_ids: list[int], current_facts: set):
        """生成并显示 Vis.js 图"""
        if not current_path_ids and not self.initial_facts:
            # self.web_view.setHtml("<html><body><h3 style='color:white;'>无数据</h3></body></html>")
            # 保持模板，只清空数据
            self._render_graph({"nodes": [], "edges": []})
            return

        nodes = []
        edges = []
        added_nodes = set()

        def add_node(node_id, label, _group):
            if node_id in added_nodes:
                return

            color = {}
            font = {"color": "#ffffff"}

            if _group == "initial_fact":
                color = {"background": "#2d4059", "border": "#decdc3"}
            elif _group == "new_fact":
                color = {"background": "#f07b3f", "border": "#decdc3"}
            elif _group == "conclusion":
                color = {"background": "#ffd460", "border": "#decdc3"}
                font = {"color": "#2d4059"}
            elif _group == "rule":
                color = {"background": "#ea5455", "border": "#decdc3"}

            nodes.append({"id": node_id, "label": label, "color": color, "font": font})
            added_nodes.add(node_id)

        # 1. 绘制事实节点
        for fact in current_facts:
            group = "new_fact"
            if fact in self.initial_facts:
                group = "initial_fact"
            if fact == self.final_conclusion:
                group = "conclusion"
            add_node(fact, fact, group)

        # 2. 绘制规则节点和连线
        for rule_id in current_path_ids:
            if rule_id >= len(self.all_rules):
                continue

            pres, ans = self.all_rules[rule_id]
            rule_node_id = f"R{rule_id}"

            add_node(rule_node_id, f"规则{rule_id}: {pres}", "rule")

            for pre in pres:
                # 确保前提节点存在（通常已在事实中）
                add_node(pre, pre, "new_fact")
                edges.append({"from": pre, "to": rule_node_id})

            # 确保结论节点存在
            add_node(ans, ans, "new_fact")
            edges.append({"from": rule_node_id, "to": ans})

        self._render_graph({"nodes": nodes, "edges": edges})


class BatchRuleAddDialog(QDialog):
    """批量添加规则对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量添加规则")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                "请输入规则，每行一条。\n格式：前提1, 前提2, ... = 结论\n例如：会飞, 下蛋 = 鸟"
            )
        )

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("会飞, 下蛋 = 鸟\n食肉, 有犬齿 = 哺乳动物")
        layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_rules(self) -> list[tuple[list[str], str]]:
        text = self.text_edit.toPlainText()
        rules = []
        for line in text.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue

            parts = line.split("=")
            if len(parts) != 2:
                continue

            premises_str, conclusion = parts
            premises = [p.strip() for p in premises_str.split(",") if p.strip()]
            conclusion = conclusion.strip()

            if premises and conclusion:
                rules.append((premises, conclusion))
        return rules


class ExpertSystemGUI(QMainWindow):
    """专家系统主窗口"""

    DEFAULT_RULES = [
        (["毛发"], "哺乳动物"),
        (["有奶"], "哺乳动物"),
        (["羽毛"], "鸟"),
        (["会飞", "下蛋"], "鸟"),
        (["吃肉"], "肉食动物"),
        (["犬齿", "有爪", "眼盯前方"], "肉食动物"),
        (["哺乳动物", "有蹄"], "蹄类动物"),
        (["哺乳动物", "反刍动物"], "蹄类动物"),
        (["哺乳动物", "肉食动物", "黄褐色", "暗斑点"], "金钱豹"),
        (["哺乳动物", "肉食动物", "黄褐色", "黑色条纹"], "老虎"),
        (["蹄类动物", "长脖子", "长腿", "暗斑点"], "长颈鹿"),
        (["蹄类动物", "黑色条纹"], "斑马"),
        (["鸟", "长脖子", "长腿", "黑白两色", "不飞"], "鸵鸟"),
        (["鸟", "游泳", "黑白两色", "不飞"], "企鹅"),
        (["鸟", "善飞"], "信天翁"),
    ]

    # 确定 rules.json 的路径
    if getattr(sys, "frozen", False):
        # 如果是打包后的 exe
        base_path = os.path.dirname(sys.executable)
    else:
        # 如果是脚本运行
        base_path = os.path.dirname(os.path.abspath(__file__))

    RULES_FILE = os.path.join(base_path, "rules.json")

    def __init__(self):
        super().__init__()
        self.brief_result_text = QTextEdit()
        self.backward_target_input = QComboBox()
        self.false_facts_list = QListWidget()
        self.known_facts_list = QListWidget()
        self.rules_list = QListWidget()
        self.graph_widget = InferenceGraphWidget()
        self.tabs = QTabWidget()
        self.setWindowTitle("基于产生式知识表示的专家系统")
        self.setMinimumSize(900, 600)

        # Web服务器状态
        self.web_server_port = 5000
        self.web_server_running = False

        # 初始化推理器
        self.rules: list[tuple[list[str], str]] = []
        self.all_atoms: set[str] = set()  # 缓存所有原子命题
        self.all_conclusions: set[str] = set()  # 缓存所有结论

        self.load_rules_from_json()
        self.reasoner = Rule_reasoner()
        self.reasoner.reset(self.rules)

        # 当前已知事实
        self.known_facts: list[list[str]] = [
            [],
            [],
        ]  # [用户添加的事实, 推理过程中确认的事实]
        self.false_facts: list[str] = []
        self.path_all: list[int] = []

        # 反向推理状态
        self.backward_target: str | None = None
        self.backward_in_progress = False

        self.setup_ui()
        self.refresh_rules_list()
        self.refresh_facts_display()

    def load_rules_from_json(self):
        """从JSON加载规则"""
        if os.path.exists(self.RULES_FILE):
            try:
                with open(self.RULES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}

                rules_data = data.get("rules") or []
                self.rules = [r for r in rules_data]
            except Exception as e:
                QMessageBox.warning(
                    self, "错误", f"加载规则失败: {e}\n将使用默认规则。"
                )
                self.rules = [(pres.copy(), ans) for pres, ans in self.DEFAULT_RULES]
        else:
            self.rules = [(pres.copy(), ans) for pres, ans in self.DEFAULT_RULES]
            self.save_rules_to_json()

        if not self.rules:
            self.rules = [(pres.copy(), ans) for pres, ans in self.DEFAULT_RULES]

        self.update_atoms_cache()

    def save_rules_to_json(self):
        """保存规则到JSON"""
        self.update_atoms_cache()
        data = {"rules": [[pres, ans] for pres, ans in self.rules]}
        try:
            with open(self.RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存规则失败: {e}")

    def update_atoms_cache(self):
        """更新原子命题和结论缓存"""
        self.all_atoms = set()
        self.all_conclusions = set()
        for pres, ans in self.rules:
            for p in pres:
                self.all_atoms.add(p)
            self.all_conclusions.add(ans)

        # 移除所有结论，确保事实列表中不包含结论
        self.all_atoms = self.all_atoms - self.all_conclusions

    @staticmethod
    def _btn(text: str, slot, *, style: str | None = None) -> QPushButton:
        """快捷创建按钮并绑定事件"""
        btn = QPushButton(text)
        if style:
            btn.setStyleSheet(style)
        btn.clicked.connect(slot)

        return btn

    def setup_ui(self):
        """设置UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 创建标签页
        # self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # --- Tab 1: 知识库与推理控制 ---
        tab1 = QWidget()
        tab1_layout = QHBoxLayout(tab1)

        # 左侧面板 - 知识库管理
        left_panel = self.create_knowledge_panel()

        # 中间面板 - 事实管理
        mid_panel = self.create_fact_panel()

        # 右侧面板 - 推理控制与简要结果
        right_panel = self.create_control_panel()

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(mid_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 350, 400])

        tab1_layout.addWidget(splitter)
        self.tabs.addTab(tab1, "知识库与推理控制")

        # --- Tab 2: 推理过程可视化 ---
        # self.graph_widget = InferenceGraphWidget()
        self.tabs.addTab(self.graph_widget, "推理过程可视化")

        # --- Tab 3: Web服务器 ---
        web_tab = self.create_web_server_panel()
        self.tabs.addTab(web_tab, "Web服务器")

    def create_web_server_panel(self) -> QWidget:
        """创建Web服务器控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 服务器控制区
        server_group = QGroupBox("Web服务器控制")
        server_layout = QVBoxLayout(server_group)

        # 端口设置
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口号:"))
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1024, 65535)
        self.port_spinbox.setValue(5000)
        port_layout.addWidget(self.port_spinbox)
        port_layout.addStretch()
        server_layout.addLayout(port_layout)

        # 启动/停止按钮
        self.web_server_btn = QPushButton("启动Web服务器")
        self.web_server_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 15px; font-size: 14px;"
        )
        self.web_server_btn.clicked.connect(self.toggle_web_server)
        server_layout.addWidget(self.web_server_btn)

        # 状态显示
        self.web_status_label = QLabel("状态: 未启动")
        self.web_status_label.setStyleSheet("color: #999; font-size: 12px;")
        server_layout.addWidget(self.web_status_label)

        # 打开浏览器按钮
        self.open_browser_btn = QPushButton("在浏览器中打开")
        self.open_browser_btn.setEnabled(False)
        self.open_browser_btn.clicked.connect(self.open_web_in_browser)
        server_layout.addWidget(self.open_browser_btn)

        layout.addWidget(server_group)

        # 说明信息
        info_group = QGroupBox("说明")
        info_layout = QVBoxLayout(info_group)
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml("""
        <h3>Web版专家系统</h3>
        <p>启动Web服务器后，可以通过浏览器访问专家系统的Web界面。</p>
        <h4>功能特性：</h4>
        <ul>
            <li>用户注册与登录系统</li>
            <li>正向推理和反向推理</li>
            <li>推理过程可视化</li>
            <li>推理历史记录管理</li>
            <li>管理员权限控制（仅管理员可修改规则库）</li>
        </ul>
        <h4>默认管理员账号：</h4>
        <p><b>用户名:</b> admin &nbsp;&nbsp; <b>密码:</b> admin123</p>
        <h4>注意事项：</h4>
        <ul>
            <li>首次使用前需构建前端（在web_frontend目录执行 npm run build）</li>
            <li>Web服务器与GUI共享同一个规则库</li>
            <li>可通过命令行参数 <code>--web</code> 仅启动Web服务器</li>
        </ul>
        """)
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)

        return panel

    def toggle_web_server(self):
        """启动或停止Web服务器"""
        try:
            from web_server import get_server_url, is_server_running, start_server
        except ImportError as e:
            QMessageBox.critical(self, "错误", f"无法导入Web服务器模块: {e}\n请确保已安装 flask 和 flask-cors")
            return

        if is_server_running():
            # 服务器已运行，无法停止（Flask在线程中运行，需重启程序才能停止）
            QMessageBox.information(
                self, "提示", 
                "Web服务器正在运行中。\n如需停止服务器，请关闭整个程序。"
            )
        else:
            port = self.port_spinbox.value()
            success, msg = start_server(port=port)
            
            if success:
                self.web_server_running = True
                self.web_server_port = port
                self.web_server_btn.setText("服务器运行中")
                self.web_server_btn.setStyleSheet(
                    "background-color: #2196F3; color: white; font-weight: bold; padding: 15px; font-size: 14px;"
                )
                self.web_status_label.setText(f"状态: 运行中 - http://localhost:{port}")
                self.web_status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
                self.open_browser_btn.setEnabled(True)
                self.port_spinbox.setEnabled(False)
                
                QMessageBox.information(self, "成功", msg)
            else:
                QMessageBox.warning(self, "启动失败", msg)

    def open_web_in_browser(self):
        """在浏览器中打开Web界面"""
        url = f"http://localhost:{self.web_server_port}"
        QDesktopServices.openUrl(QUrl(url))

    def create_knowledge_panel(self) -> QWidget:
        """创建知识库管理面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 规则列表
        rules_group = QGroupBox("知识库 - 规则列表")
        rules_layout = QVBoxLayout(rules_group)

        # self.rules_list = QListWidget()
        self.rules_list.itemDoubleClicked.connect(self.edit_rule)
        rules_layout.addWidget(self.rules_list)

        # 规则操作按钮
        rules_btn_layout = QHBoxLayout()

        rules_btn_layout.addWidget(self._btn("添加规则", self.add_rule))
        rules_btn_layout.addWidget(self._btn("批量添加", self.batch_add_rules))
        rules_btn_layout.addWidget(self._btn("编辑规则", self.edit_selected_rule))
        rules_btn_layout.addWidget(self._btn("删除规则", self.delete_rule))

        rules_layout.addLayout(rules_btn_layout)

        rules_layout.addWidget(self._btn("重置为默认规则", self.reset_rules))

        layout.addWidget(rules_group)

        return panel

    def create_fact_panel(self) -> QWidget:
        """创建事实管理面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 事实输入
        facts_group = QGroupBox("事实管理")
        facts_layout = QVBoxLayout(facts_group)

        # 添加事实按钮
        facts_layout.addWidget(
            self._btn("选择/添加事实", self.open_fact_selection_dialog)
        )

        def create_qlist_widget():
            list_widget = QListWidget()
            list_widget.setViewMode(QListWidget.ViewMode.IconMode)
            list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
            list_widget.setSpacing(4)
            list_widget.setMovement(QListWidget.Movement.Static)
            return list_widget

        # 已知事实列表
        facts_layout.addWidget(QLabel("已知事实 (双击移除):"))
        self.known_facts_list = create_qlist_widget()

        self.known_facts_list.itemDoubleClicked.connect(self.remove_known_fact)
        facts_layout.addWidget(self.known_facts_list)

        # 已知为假的事实
        facts_layout.addWidget(QLabel("已知为假 (双击移除):"))
        self.false_facts_list = create_qlist_widget()

        self.false_facts_list.itemDoubleClicked.connect(self.remove_false_fact)
        facts_layout.addWidget(self.false_facts_list)

        # 清空事实按钮
        facts_layout.addWidget(self._btn("清空所有事实", self.clear_facts))

        layout.addWidget(facts_group)
        return panel

    def create_control_panel(self) -> QWidget:
        """创建推理控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 推理控制
        inference_group = QGroupBox("推理控制")
        inference_layout = QVBoxLayout(inference_group)

        # 正向推理
        inference_layout.addWidget(
            self._btn(
                "正向推理",
                self.forward_inference,
                style="background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;",
            )
        )

        # 反向推理
        backward_layout = QHBoxLayout()

        # self.backward_target_input = QComboBox()
        self.backward_target_input.setEditable(True)
        self.backward_target_input.setPlaceholderText("选择或输入目标结论")
        self.update_backward_targets()

        backward_layout.addWidget(self.backward_target_input)

        backward_layout.addWidget(
            self._btn(
                "反向推理",
                self.start_backward_inference,
                style="background-color: #2196F3; color: white; font-weight: bold;",
            )
        )
        inference_layout.addLayout(backward_layout)

        layout.addWidget(inference_group)

        # 简要结果展示
        result_group = QGroupBox("推理结果摘要")
        result_layout = QVBoxLayout(result_group)
        # self.brief_result_text = QTextEdit()
        self.brief_result_text.setReadOnly(True)
        result_layout.addWidget(self.brief_result_text)

        # 查看详细过程按钮
        result_layout.addWidget(
            self._btn(
                "查看推理过程详情 >>",
                lambda: self.tabs.setCurrentIndex(1),
                style="font-weight: bold; padding: 5px;",
            )
        )

        layout.addWidget(result_group)

        return panel

    def refresh_rules_list(self):
        """刷新规则列表"""
        self.rules_list.clear()
        for i, (pres, ans) in enumerate(self.rules):
            if pres:
                item = QListWidgetItem(f"规则{i}: {' + '.join(pres)} → {ans}")
                item.setData(Qt.ItemDataRole.UserRole, i)
                self.rules_list.addItem(item)

    def refresh_facts_display(self):
        """刷新事实显示"""
        self.known_facts_list.clear()
        self.known_facts_list.addItems(self.known_facts[0])
        self.known_facts_list.addItems(["*" + x for x in self.known_facts[1]])

        self.false_facts_list.clear()
        self.false_facts_list.addItems(self.false_facts)

    def update_backward_targets(self):
        """更新反向推理目标列表"""
        current_text = self.backward_target_input.currentText()
        self.backward_target_input.clear()
        self.backward_target_input.addItems(sorted(list(self.all_conclusions)))
        self.backward_target_input.setEditText(current_text)

    def sync_reasoner_facts(self):
        """同步事实到推理器"""
        self.reasoner.clear_known()
        if self.known_facts:
            self.reasoner.add_known(self.known_facts[0])
        self.reasoner.clear_false()
        if self.false_facts:
            self.reasoner.add_false(self.false_facts)

    def _update_system_state(
        self,
        *,
        save: bool = True,
        refresh_rules: bool = True,
        refresh_targets: bool = True,
    ):
        """统一的规则变更后更新逻辑"""
        # 更新缓存
        if save:
            self.save_rules_to_json()
        else:
            self.update_atoms_cache()

        # 重置推理机并刷新 UI
        self.reasoner.reset(self.rules)
        if refresh_rules:
            self.refresh_rules_list()
        if refresh_targets:
            self.update_backward_targets()

    def open_fact_selection_dialog(self):
        """打开事实选择对话框"""
        dialog = FactSelectionDialog(
            list(self.all_atoms), self.known_facts[0], self.known_facts[1]
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_facts = dialog.get_selected_facts()
            if len(set(self.known_facts[0]) - set(selected_facts)) > 0:
                self.path_all = []
                self.known_facts[1].clear()
                self.backward_in_progress = False

            # 更新已知事实
            self.known_facts[0] = selected_facts
            self.reasoner.add_known(selected_facts)
            self.refresh_facts_display()

    def remove_known_fact(self, item: QListWidgetItem):
        """移除已知事实"""
        fact = item.text()
        if fact in self.known_facts[0]:
            self.known_facts[0].remove(fact)
            self.known_facts[1].clear()
            self.sync_reasoner_facts()
            self.refresh_facts_display()
            self.path_all.clear()

    def remove_false_fact(self, item: QListWidgetItem):
        """移除已知为假的事实"""
        fact = item.text()
        if fact in self.false_facts:
            self.false_facts.remove(fact)
            self.sync_reasoner_facts()
            self.refresh_facts_display()

    def add_rule(self):
        """添加新规则"""
        dialog = RuleEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            premises, conclusion = dialog.get_rule()
            if premises and conclusion:
                self.rules.append((premises.copy(), conclusion))
                self._update_system_state()
                QMessageBox.information(self, "成功", "规则添加成功！")

    def batch_add_rules(self):
        """批量添加规则"""
        dialog = BatchRuleAddDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_rules = dialog.get_rules()
            if new_rules:
                self.rules.extend(new_rules)
                self._update_system_state()
                QMessageBox.information(
                    self, "成功", f"成功添加 {len(new_rules)} 条规则！"
                )

    def edit_selected_rule(self):
        """编辑选中的规则"""
        current_item = self.rules_list.currentItem()
        if current_item:
            self.edit_rule(current_item)
        else:
            QMessageBox.warning(self, "提示", "请先选择一条规则")

    def edit_rule(self, item: QListWidgetItem):
        """编辑规则"""
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        pres, ans = self.rules[rule_id]

        dialog = RuleEditDialog(self, pres, ans)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_pres, new_ans = dialog.get_rule()
            if new_pres and new_ans:
                self.rules[rule_id] = (new_pres.copy(), new_ans)
                self._update_system_state()
                QMessageBox.information(self, "成功", "规则修改成功！")

    def delete_rule(self):
        """删除选中的规则"""
        current_item = self.rules_list.currentItem()
        if current_item:
            rule_id = current_item.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除规则{rule_id}吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.rules.pop(rule_id)
                self._update_system_state()
        else:
            QMessageBox.warning(self, "提示", "请先选择一条规则")

    def reset_rules(self):
        """重置为默认规则"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置为默认规则吗？这将清除所有修改。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.rules = [(pres.copy(), ans) for pres, ans in self.DEFAULT_RULES]
            self._update_system_state()
            self.clear_facts()
            QMessageBox.information(self, "成功", "规则已重置！")

    def clear_facts(self):
        """清空所有事实"""
        self.known_facts = [[], []]
        self.false_facts.clear()
        self.path_all.clear()
        self.sync_reasoner_facts()
        self.refresh_facts_display()
        self.backward_in_progress = False

    def update_known_facts_from_path(self, path: list[int]):
        """根据推理路径更新已知事实列表 (使用全局 self.rules)"""
        self.path_all += [r for r in path if r not in self.path_all]
        derived_facts = set()
        for rule_id in path:
            if rule_id < len(self.rules):
                derived_facts.add(self.rules[rule_id][1])

        # 识别真正的新事实
        new_facts = derived_facts - set(self.known_facts[1])

        if new_facts:
            self.known_facts[1].extend(sorted(list(new_facts)))
            self.refresh_facts_display()

    def forward_inference(self):
        """正向推理"""
        if not self.known_facts[0]:
            QMessageBox.warning(self, "提示", "请先添加一些已知事实！")
            return

        # 执行正向推理
        conclusions, path = self.reasoner.find()

        # 冲突消解：如果有多个结论，优先选择规则链最长的
        result_msg: str
        final_conclusion = ""

        if len(conclusions) > 1:
            result_msg = "发现多个可能的结论（冲突消解）:\n\n"
            for i, conc in enumerate(conclusions):
                result_msg += f"{i + 1}. {conc}\n"
            result_msg += f"\n采用结论: {conclusions[0]} (优先级最高)"
            final_conclusion = conclusions[0]
        elif conclusions:
            result_msg = f"推理成功！\n\n结论: {conclusions[0]}"
            final_conclusion = conclusions[0]
        else:
            if path:
                result_msg = "推理结束。未能得出特定结论，但产生了一些中间推导。"
            else:
                result_msg = "无法推出新的结论。\n\n建议添加更多事实后重试。"
                self.brief_result_text.setText(result_msg)
                # 提示用户补充事实
                self.prompt_for_facts()
                return

        # 更新简要结果
        self.brief_result_text.setText(result_msg)

        # 更新已知事实列表 (包含推出的结论)
        self.update_known_facts_from_path(path)
        # 更新可视化组件
        self.graph_widget.set_data(
            self.path_all, self.rules, self.known_facts[0], final_conclusion, result_msg
        )

    def prompt_for_facts(self):
        """提示用户补充事实"""
        reply = QMessageBox.question(
            self,
            "需要更多信息",
            "当前已知事实不足以得出结论。\n是否要添加更多事实？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.open_fact_selection_dialog()
            # 重新推理
            self.forward_inference()

    def start_backward_inference(self):
        """开始反向推理"""
        target = self.backward_target_input.currentText().strip()
        if not target:
            QMessageBox.warning(self, "提示", "请输入目标结论！")
            return

        self.backward_target = target
        self.backward_in_progress = True

        # 循环执行推理直到成功、失败或用户取消
        while self.backward_in_progress:
            status, data, path = self.reasoner.step_backward(self.backward_target)
            self.update_known_facts_from_path(path)
            if status == 0:  # 成功
                self.backward_in_progress = False
                result_msg = (
                    f"反向推理成功！\n\n目标 '{self.backward_target}' 已证明成立。"
                )
                self.brief_result_text.setText(result_msg)

                self.graph_widget.set_data(
                    self.path_all,
                    self.rules,
                    self.known_facts[0],
                    self.backward_target,
                    result_msg,
                )
                QMessageBox.information(self, "成功", result_msg)

            elif status == 1:  # 失败
                self.backward_in_progress = False
                result_msg = (
                    f"反向推理失败。\n\n无法证明目标 '{self.backward_target}' 成立。"
                )
                self.brief_result_text.setText(result_msg)

                self.graph_widget.set_data(
                    self.path_all, self.rules, self.known_facts[0], "", result_msg
                )
                QMessageBox.warning(self, "失败", result_msg)

            elif status == 2:  # 需要询问
                # 弹出对话框询问用户

                dialog = FactQueryDialog(
                    [d for d in data if d not in self.known_facts[0]], self
                )
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    true_facts = dialog.get_true_facts()
                    # 将选中的事实加入已知事实
                    if true_facts:
                        self.reasoner.add_known(true_facts)
                        for f in true_facts:
                            self.known_facts[0].append(f)

                    # 未选中的为假
                    false_facts = [f for f in data if f not in true_facts]
                    if false_facts:
                        self.reasoner.add_false(false_facts)
                        for f in false_facts:
                            if f not in self.false_facts:
                                self.false_facts.append(f)

                    self.refresh_facts_display()
                else:
                    # 用户取消，视为全部为假或停止推理
                    # 视为全部为假
                    self.reasoner.add_false(data)
                    for f in data:
                        if f not in self.false_facts:
                            self.false_facts.append(f)
                    self.refresh_facts_display()


def run_web_server_only(host: str = '0.0.0.0', port: int = 5000):
    """仅运行Web服务器（无GUI）"""
    try:
        from web_server import app
        print("=" * 50)
        print("  专家系统 - Web服务器模式")
        print("=" * 50)
        print(f"访问地址: http://localhost:{port}")
        print("默认管理员: admin / admin123")
        print("按 Ctrl+C 停止服务器")
        print("=" * 50)
        app.run(host=host, port=port, debug=False)
    except ImportError as e:
        print(f"错误: 无法导入Web服务器模块 - {e}")
        print("请确保已安装 flask 和 flask-cors:")
        print("  pip install flask flask-cors")
        sys.exit(1)


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='基于产生式知识表示的专家系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python expert_system_gui.py          # 启动GUI
  python expert_system_gui.py --web    # 仅启动Web服务器
  python expert_system_gui.py --web --port 8080  # 指定端口启动Web服务器
        """
    )
    parser.add_argument('--web', action='store_true', 
                        help='仅启动Web服务器（不显示GUI）')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Web服务器监听地址（默认: 0.0.0.0）')
    parser.add_argument('--port', type=int, default=5000,
                        help='Web服务器端口（默认: 5000）')
    
    args = parser.parse_args()
    
    if args.web:
        # 仅Web服务器模式
        run_web_server_only(host=args.host, port=args.port)
    else:
        # GUI模式
        app = QApplication(sys.argv)

        # 设置中文字体
        font = QFont("Microsoft YaHei", 10)
        app.setFont(font)

        window = ExpertSystemGUI()
        window.show()

        sys.exit(app.exec())


if __name__ == "__main__":
    main()
