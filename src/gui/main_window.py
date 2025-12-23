"""专家系统主窗口"""

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core import RuleReasoner
from src.data import DEFAULT_RULES, DataStorage

from .dialogs import (
    BatchRuleAddDialog,
    FactQueryDialog,
    FactSelectionDialog,
    RuleEditDialog,
)
from .graph_widget import InferenceGraphWidget


class ExpertSystemGUI(QMainWindow):
    """专家系统主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("基于产生式知识表示的专家系统")
        self.setMinimumSize(900, 600)

        # 数据存储
        self.storage = DataStorage()

        # Web服务器状态
        self.web_server_port = 5000
        self.web_server_running = False

        # 初始化推理器
        self.rules: list[tuple[list[str], str]] = []
        self.all_atoms: set[str] = set()
        self.all_conclusions: set[str] = set()

        self._load_rules()
        self.reasoner = RuleReasoner()
        self.reasoner.reset(self.rules)

        # 当前已知事实 [用户添加的事实, 推理过程中确认的事实]
        self.known_facts: list[list[str]] = [[], []]
        self.false_facts: list[str] = []
        self.path_all: list[int] = []

        # 反向推理状态
        self.backward_target: str | None = None
        self.backward_in_progress = False

        # UI 组件
        self.tabs = QTabWidget()
        self.rules_list = QListWidget()
        self.known_facts_list = QListWidget()
        self.false_facts_list = QListWidget()
        self.backward_target_input = QComboBox()
        self.brief_result_text = QTextEdit()
        self.graph_widget = InferenceGraphWidget()

        self._setup_ui()
        self._refresh_rules_list()
        self._refresh_facts_display()

    def _load_rules(self):
        """从存储加载规则"""
        try:
            self.rules = self.storage.load_rules()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载规则失败: {e}\n将使用默认规则。")
            self.rules = [(list(pres), ans) for pres, ans in DEFAULT_RULES]
        self._update_atoms_cache()

    def _save_rules(self):
        """保存规则到存储"""
        self._update_atoms_cache()
        try:
            self.storage.save_rules(self.rules)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存规则失败: {e}")

    def _update_atoms_cache(self):
        """更新原子命题和结论缓存"""
        self.all_atoms = set()
        self.all_conclusions = set()
        for pres, ans in self.rules:
            self.all_atoms.update(pres)
            self.all_conclusions.add(ans)
        self.all_atoms -= self.all_conclusions

    def _setup_ui(self):
        """设置UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(self.tabs)

        # Tab 1: 知识库与推理控制
        tab1 = QWidget()
        tab1_layout = QHBoxLayout(tab1)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._create_knowledge_panel())
        splitter.addWidget(self._create_fact_panel())
        splitter.addWidget(self._create_control_panel())
        splitter.setSizes([350, 350, 400])
        tab1_layout.addWidget(splitter)
        self.tabs.addTab(tab1, "知识库与推理控制")

        # Tab 2: 推理过程可视化
        self.tabs.addTab(self.graph_widget, "推理过程可视化")

        # Tab 3: Web服务器
        self.tabs.addTab(self._create_web_server_panel(), "Web服务器")

    def _btn(self, text: str, slot, *, style: str | None = None) -> QPushButton:
        """快捷创建按钮"""
        btn = QPushButton(text)
        if style:
            btn.setStyleSheet(style)
        btn.clicked.connect(slot)
        return btn

    def _create_knowledge_panel(self) -> QWidget:
        """创建知识库管理面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        rules_group = QGroupBox("知识库 - 规则列表")
        rules_layout = QVBoxLayout(rules_group)
        self.rules_list.itemDoubleClicked.connect(self._edit_rule)
        rules_layout.addWidget(self.rules_list)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self._btn("添加规则", self._add_rule))
        btn_layout.addWidget(self._btn("批量添加", self._batch_add_rules))
        btn_layout.addWidget(self._btn("编辑规则", self._edit_selected_rule))
        btn_layout.addWidget(self._btn("删除规则", self._delete_rule))
        rules_layout.addLayout(btn_layout)
        rules_layout.addWidget(self._btn("重置为默认规则", self._reset_rules))

        layout.addWidget(rules_group)
        return panel

    def _create_fact_panel(self) -> QWidget:
        """创建事实管理面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        facts_group = QGroupBox("事实管理")
        facts_layout = QVBoxLayout(facts_group)
        facts_layout.addWidget(
            self._btn("选择/添加事实", self._open_fact_selection_dialog)
        )

        def create_list_widget():
            lw = QListWidget()
            lw.setViewMode(QListWidget.ViewMode.IconMode)
            lw.setResizeMode(QListWidget.ResizeMode.Adjust)
            lw.setSpacing(4)
            lw.setMovement(QListWidget.Movement.Static)
            return lw

        facts_layout.addWidget(QLabel("已知事实 (双击移除):"))
        self.known_facts_list = create_list_widget()
        self.known_facts_list.itemDoubleClicked.connect(self._remove_known_fact)
        facts_layout.addWidget(self.known_facts_list)

        facts_layout.addWidget(QLabel("已知为假 (双击移除):"))
        self.false_facts_list = create_list_widget()
        self.false_facts_list.itemDoubleClicked.connect(self._remove_false_fact)
        facts_layout.addWidget(self.false_facts_list)

        facts_layout.addWidget(self._btn("清空所有事实", self._clear_facts))
        layout.addWidget(facts_group)
        return panel

    def _create_control_panel(self) -> QWidget:
        """创建推理控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        inference_group = QGroupBox("推理控制")
        inference_layout = QVBoxLayout(inference_group)

        inference_layout.addWidget(
            self._btn(
                "正向推理",
                self._forward_inference,
                style="background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;",
            )
        )

        backward_layout = QHBoxLayout()
        self.backward_target_input.setEditable(True)
        self.backward_target_input.setPlaceholderText("选择或输入目标结论")
        self._update_backward_targets()
        backward_layout.addWidget(self.backward_target_input)
        backward_layout.addWidget(
            self._btn(
                "反向推理",
                self._start_backward_inference,
                style="background-color: #2196F3; color: white; font-weight: bold;",
            )
        )
        inference_layout.addLayout(backward_layout)
        layout.addWidget(inference_group)

        result_group = QGroupBox("推理结果摘要")
        result_layout = QVBoxLayout(result_group)
        self.brief_result_text.setReadOnly(True)
        result_layout.addWidget(self.brief_result_text)
        result_layout.addWidget(
            self._btn(
                "查看推理过程详情 >>",
                lambda: self.tabs.setCurrentIndex(1),
                style="font-weight: bold; padding: 5px;",
            )
        )
        layout.addWidget(result_group)
        return panel

    def _create_web_server_panel(self) -> QWidget:
        """创建Web服务器控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        server_group = QGroupBox("Web服务器控制")
        server_layout = QVBoxLayout(server_group)

        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口号:"))
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1024, 65535)
        self.port_spinbox.setValue(5000)
        port_layout.addWidget(self.port_spinbox)
        port_layout.addStretch()
        server_layout.addLayout(port_layout)

        self.web_server_btn = QPushButton("启动Web服务器")
        self.web_server_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 15px; font-size: 14px;"
        )
        self.web_server_btn.clicked.connect(self._toggle_web_server)
        server_layout.addWidget(self.web_server_btn)

        self.web_status_label = QLabel("状态: 未启动")
        self.web_status_label.setStyleSheet("color: #999; font-size: 12px;")
        server_layout.addWidget(self.web_status_label)

        self.open_browser_btn = QPushButton("在浏览器中打开")
        self.open_browser_btn.setEnabled(False)
        self.open_browser_btn.clicked.connect(self._open_web_in_browser)
        server_layout.addWidget(self.open_browser_btn)

        layout.addWidget(server_group)

        info_group = QGroupBox("说明")
        info_layout = QVBoxLayout(info_group)
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml(
            """
        <h3>Web版专家系统</h3>
        <p>启动Web服务器后，可以通过浏览器访问专家系统的Web界面。</p>
        <h4>默认管理员账号：</h4>
        <p><b>用户名:</b> admin &nbsp;&nbsp; <b>密码:</b> admin123</p>
        """
        )
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)
        return panel

    # ========== 规则管理 ==========

    def _refresh_rules_list(self):
        self.rules_list.clear()
        for i, (pres, ans) in enumerate(self.rules):
            if pres:
                item = QListWidgetItem(f"规则{i}: {' + '.join(pres)} → {ans}")
                item.setData(Qt.ItemDataRole.UserRole, i)
                self.rules_list.addItem(item)

    def _update_system_state(self, *, save: bool = True):
        """规则变更后更新系统状态"""
        if save:
            self._save_rules()
        else:
            self._update_atoms_cache()
        self.reasoner.reset(self.rules)
        self._refresh_rules_list()
        self._update_backward_targets()

    def _add_rule(self):
        dialog = RuleEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            premises, conclusion = dialog.get_rule()
            if premises and conclusion:
                self.rules.append((list(premises), conclusion))
                self._update_system_state()
                QMessageBox.information(self, "成功", "规则添加成功！")

    def _batch_add_rules(self):
        dialog = BatchRuleAddDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_rules = dialog.get_rules()
            if new_rules:
                self.rules.extend(new_rules)
                self._update_system_state()
                QMessageBox.information(
                    self, "成功", f"成功添加 {len(new_rules)} 条规则！"
                )

    def _edit_selected_rule(self):
        current_item = self.rules_list.currentItem()
        if current_item:
            self._edit_rule(current_item)
        else:
            QMessageBox.warning(self, "提示", "请先选择一条规则")

    def _edit_rule(self, item: QListWidgetItem):
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        pres, ans = self.rules[rule_id]
        dialog = RuleEditDialog(self, pres, ans)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_pres, new_ans = dialog.get_rule()
            if new_pres and new_ans:
                self.rules[rule_id] = (list(new_pres), new_ans)
                self._update_system_state()
                QMessageBox.information(self, "成功", "规则修改成功！")

    def _delete_rule(self):
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

    def _reset_rules(self):
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置为默认规则吗？这将清除所有修改。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.rules = [(list(pres), ans) for pres, ans in DEFAULT_RULES]
            self._update_system_state()
            self._clear_facts()
            QMessageBox.information(self, "成功", "规则已重置！")

    # ========== 事实管理 ==========

    def _refresh_facts_display(self):
        self.known_facts_list.clear()
        self.known_facts_list.addItems(self.known_facts[0])
        self.known_facts_list.addItems(["*" + x for x in self.known_facts[1]])
        self.false_facts_list.clear()
        self.false_facts_list.addItems(self.false_facts)

    def _update_backward_targets(self):
        current_text = self.backward_target_input.currentText()
        self.backward_target_input.clear()
        self.backward_target_input.addItems(sorted(self.all_conclusions))
        self.backward_target_input.setEditText(current_text)

    def _sync_reasoner_facts(self):
        self.reasoner.clear_known()
        if self.known_facts:
            self.reasoner.add_known(self.known_facts[0])
        self.reasoner.clear_false()
        if self.false_facts:
            self.reasoner.add_false(self.false_facts)

    def _open_fact_selection_dialog(self):
        dialog = FactSelectionDialog(
            list(self.all_atoms), self.known_facts[0], self.known_facts[1]
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_facts = dialog.get_selected_facts()
            # 如果移除了事实，需要重置推理状态
            if set(self.known_facts[0]) - set(selected_facts):
                self.path_all = []
                self.known_facts[1].clear()
                self.backward_in_progress = False
            self.known_facts[0] = selected_facts
            # 重新同步推理器状态（先清空再添加）
            self._sync_reasoner_facts()
            self._refresh_facts_display()

    def _remove_known_fact(self, item: QListWidgetItem):
        fact = item.text()
        if fact in self.known_facts[0]:
            self.known_facts[0].remove(fact)
            self.known_facts[1].clear()
            self._sync_reasoner_facts()
            self._refresh_facts_display()
            self.path_all.clear()

    def _remove_false_fact(self, item: QListWidgetItem):
        fact = item.text()
        if fact in self.false_facts:
            self.false_facts.remove(fact)
            self._sync_reasoner_facts()
            self._refresh_facts_display()

    def _clear_facts(self):
        self.known_facts = [[], []]
        self.false_facts.clear()
        self.path_all.clear()
        self._sync_reasoner_facts()
        self._refresh_facts_display()
        self.backward_in_progress = False

    # ========== 推理 ==========

    def _update_known_facts_from_path(self, path: list[int]):
        self.path_all += [r for r in path if r not in self.path_all]
        derived_facts = set()
        for rule_id in path:
            if rule_id < len(self.rules):
                derived_facts.add(self.rules[rule_id][1])
        new_facts = derived_facts - set(self.known_facts[1])
        if new_facts:
            self.known_facts[1].extend(sorted(new_facts))
            self._refresh_facts_display()

    def _forward_inference(self):
        if not self.known_facts[0]:
            QMessageBox.warning(self, "提示", "请先添加一些已知事实！")
            return

        conclusions, path = self.reasoner.find()

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
                final_conclusion = ""
            else:
                result_msg = "无法推出新的结论。\n\n建议添加更多事实后重试。"
                self.brief_result_text.setText(result_msg)
                return

        self.brief_result_text.setText(result_msg)
        self._update_known_facts_from_path(path)
        self.graph_widget.set_data(
            self.path_all, self.rules, self.known_facts[0], final_conclusion, result_msg
        )

    def _start_backward_inference(self):
        target = self.backward_target_input.currentText().strip()
        if not target:
            QMessageBox.warning(self, "提示", "请输入目标结论！")
            return

        self.backward_target = target
        self.backward_in_progress = True

        while self.backward_in_progress:
            status, data, path = self.reasoner.step_backward(self.backward_target)
            self._update_known_facts_from_path(path)

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
                dialog = FactQueryDialog(
                    [d for d in data if d not in self.known_facts[0]], self
                )
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    true_facts = dialog.get_true_facts()
                    if true_facts:
                        self.reasoner.add_known(true_facts)
                        self.known_facts[0].extend(true_facts)
                    false_facts = [f for f in data if f not in true_facts]
                    if false_facts:
                        self.reasoner.add_false(false_facts)
                        self.false_facts.extend(
                            f for f in false_facts if f not in self.false_facts
                        )
                    self._refresh_facts_display()
                else:
                    self.reasoner.add_false(data)
                    self.false_facts.extend(
                        f for f in data if f not in self.false_facts
                    )
                    self._refresh_facts_display()

    # ========== Web服务器 ==========

    def _toggle_web_server(self):
        try:
            from src.web import is_server_running, start_server
        except ImportError as e:
            QMessageBox.critical(self, "错误", f"无法导入Web服务器模块: {e}")
            return

        if is_server_running():
            QMessageBox.information(
                self, "提示", "Web服务器正在运行中。\n如需停止服务器，请关闭整个程序。"
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

    def _open_web_in_browser(self):
        QDesktopServices.openUrl(QUrl(f"http://localhost:{self.web_server_port}"))
