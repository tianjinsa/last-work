"""推理路径图可视化组件"""

import json

from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# vis.js 图形模板
_VIS_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body { margin: 0; padding: 0; background-color: #1e1e1e; height: 100vh; overflow: hidden; }
    #mynetwork { width: 100%; height: 100%; }
  </style>
</head>
<body>
  <div id='mynetwork'></div>
  <script>
    var network = null;
    window.updateGraph = function(graphData) {
      var container = document.getElementById('mynetwork');
      var data = {
        nodes: new vis.DataSet(graphData.nodes),
        edges: new vis.DataSet(graphData.edges)
      };
      var options = {
        nodes: {
          shape: 'box',
          font: { color: '#ffffff', size: 16, face: 'Microsoft YaHei' },
          borderWidth: 1, shadow: true, margin: 10,
          widthConstraint: { maximum: 100 }
        },
        edges: {
          arrows: 'to',
          color: { color: '#decdc3', highlight: '#ffffff' },
          smooth: { type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.5 }
        },
        layout: {
          hierarchical: {
            direction: 'DU', sortMethod: 'directed',
            levelSeparation: 120, nodeSpacing: 150,
            blockShifting: true, edgeMinimization: true, parentCentralization: true
          }
        },
        physics: {
          enabled: true,
          hierarchicalRepulsion: {
            centralGravity: 0.3, springLength: 120, springConstant: 1,
            nodeDistance: 120, damping: 1
          },
          solver: 'hierarchicalRepulsion'
        }
      };
      if (network !== null) { network.destroy(); network = null; }
      network = new vis.Network(container, data, options);
      network.on('dragStart', function() { network.setOptions({ physics: { enabled: false } }); });
      network.on('dragEnd', function() { network.setOptions({ physics: { enabled: true } }); });
    };
  </script>
</body>
</html>"""


class InferenceGraphWidget(QWidget):
    """推理路径图显示组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # 图形显示区域
        self.web_view = QWebEngineView()
        page = self.web_view.page()
        if page:
            page.setBackgroundColor(Qt.GlobalColor.transparent)
        layout.addWidget(self.web_view, stretch=4)

        # 控制区域
        controls_layout = QHBoxLayout()
        self.prev_btn = QPushButton("上一步")
        self.prev_btn.clicked.connect(self._go_prev)
        controls_layout.addWidget(self.prev_btn)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self._on_slider_changed)
        controls_layout.addWidget(self.slider)

        self.next_btn = QPushButton("下一步")
        self.next_btn.clicked.connect(self._go_next)
        controls_layout.addWidget(self.next_btn)

        self.step_label = QLabel("步骤: 0/0")
        controls_layout.addWidget(self.step_label)
        layout.addLayout(controls_layout)

        # 信息展示区域
        info_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 推理解释
        exp_group = QGroupBox("推理解释")
        exp_layout = QVBoxLayout(exp_group)
        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        exp_layout.addWidget(self.explanation_text)
        info_splitter.addWidget(exp_group)

        # 综合数据库
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
        self.step_states: list[dict] = []
        self.web_ready = False
        self._pending_graph: dict | None = None

        self._init_web_view()

    def _init_web_view(self):
        def on_load_finished(_ok: bool):
            self.web_ready = True
            if self._pending_graph is not None:
                self._render_graph(self._pending_graph)
                self._pending_graph = None

        self.web_view.loadFinished.connect(on_load_finished)
        self.web_view.setHtml(_VIS_TEMPLATE)

    def _render_graph(self, graph_data: dict):
        if self.web_ready:
            js = f"window.updateGraph({json.dumps(graph_data)})"
            page = self.web_view.page()
            if page:
                page.runJavaScript(js)
        else:
            self._pending_graph = graph_data

    def set_data(
        self,
        path: list[int],
        all_rules: list[tuple[list[str], str]],
        initial_facts: list[str],
        conclusion: str,
        result_msg: str,
    ):
        """设置推理数据并初始化视图"""
        self.path = path
        self.all_rules = all_rules
        self.initial_facts = list(initial_facts)
        self.final_conclusion = conclusion
        self.result_text.setText(result_msg)

        self._precalculate_steps()

        total_steps = len(path)
        self.slider.setRange(0, total_steps)
        self.slider.setValue(total_steps)
        self._update_view(total_steps)

    def _precalculate_steps(self):
        """预计算每一步的状态"""
        self.step_states = []
        current_facts = set(self.initial_facts)

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

    def _go_prev(self):
        val = self.slider.value()
        if val > 0:
            self.slider.setValue(val - 1)

    def _go_next(self):
        val = self.slider.value()
        if val < self.slider.maximum():
            self.slider.setValue(val + 1)

    def _on_slider_changed(self, value):
        self._update_view(value)

    def _update_view(self, step):
        """更新视图到指定步骤"""
        self.step_label.setText(f"步骤: {step}/{len(self.path)}")

        if step < len(self.step_states):
            state = self.step_states[step]

            self.database_list.clear()
            for fact in sorted(state["facts"]):
                item = QListWidgetItem(fact)
                self.database_list.addItem(item)

            self.explanation_text.setText(state["explanation"])
            self._draw_graph(state["path_ids"], state["facts"])

    def _draw_graph(self, current_path_ids: list[int], current_facts: set):
        """生成并显示图"""
        if not current_path_ids and not self.initial_facts:
            self._render_graph({"nodes": [], "edges": []})
            return

        nodes, edges = [], []
        added_nodes: set[str] = set()

        def add_node(node_id: str, label: str, group: str):
            if node_id in added_nodes:
                return
            color_map = {
                "initial_fact": {"background": "#2d4059", "border": "#decdc3"},
                "new_fact": {"background": "#f07b3f", "border": "#decdc3"},
                "conclusion": {"background": "#ffd460", "border": "#decdc3"},
                "rule": {"background": "#ea5455", "border": "#decdc3"},
            }
            font_color = "#2d4059" if group == "conclusion" else "#ffffff"
            nodes.append(
                {
                    "id": node_id,
                    "label": label,
                    "color": color_map.get(group, {}),
                    "font": {"color": font_color},
                }
            )
            added_nodes.add(node_id)

        # 绘制事实节点
        for fact in current_facts:
            group = "initial_fact" if fact in self.initial_facts else "new_fact"
            if fact == self.final_conclusion:
                group = "conclusion"
            add_node(fact, fact, group)

        # 绘制规则节点和连线
        for rule_id in current_path_ids:
            if rule_id >= len(self.all_rules):
                continue
            pres, ans = self.all_rules[rule_id]
            rule_node_id = f"R{rule_id}"
            add_node(rule_node_id, f"规则{rule_id}: {pres}", "rule")

            for pre in pres:
                add_node(pre, pre, "new_fact")
                edges.append({"from": pre, "to": rule_node_id})

            add_node(ans, ans, "new_fact")
            edges.append({"from": rule_node_id, "to": ans})

        self._render_graph({"nodes": nodes, "edges": edges})
