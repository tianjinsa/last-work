"""GUI 对话框组件"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


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
        content_layout = QHBoxLayout()

        # 左边: 可选事实
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("可选事实 (点击添加):"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索事实...")
        self.search_input.textChanged.connect(self._refresh_lists)
        left_layout.addWidget(self.search_input)

        self.available_list = QListWidget()
        self.available_list.itemClicked.connect(self._add_fact)
        left_layout.addWidget(self.available_list)
        content_layout.addWidget(left_widget)

        # 右边: 已选事实
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("已选事实 (点击移除):"))

        self.selected_list = QListWidget()
        self.selected_list.itemClicked.connect(self._remove_fact)
        right_layout.addWidget(self.selected_list)
        content_layout.addWidget(right_widget)

        main_layout.addLayout(content_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self._refresh_lists()

    def _refresh_lists(self):
        self.available_list.clear()
        self.selected_list.clear()

        search_text = self.search_input.text().lower()
        self.available_list.addItems(
            [f for f in sorted(self.all_facts) if search_text in f.lower()]
        )

        for fact in sorted(self.stop_facts):
            item = QListWidgetItem("*" + fact)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            font = item.font()
            font.setItalic(True)
            item.setFont(font)
            item.setToolTip("中间事实，无法移除")
            self.selected_list.addItem(item)
        self.selected_list.addItems(sorted(self.selected_facts))

    def _add_fact(self, item):
        fact = item.text()
        self.selected_facts.add(fact)
        self.all_facts.discard(fact)
        self._refresh_lists()

    def _remove_fact(self, item):
        fact = item.text()
        if fact.startswith("*"):
            return
        self.all_facts.add(fact)
        self.selected_facts.discard(fact)
        self._refresh_lists()

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
    """事实询问对话框（反向推理时使用）"""

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
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText("确认选中为真")
        if cancel_btn:
            cancel_btn.setText("全部为假/取消")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_true_facts(self) -> list[str]:
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]


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
