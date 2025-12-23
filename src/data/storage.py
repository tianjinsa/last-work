"""数据存储管理"""

import json
import os
import sys
from datetime import datetime

from .constants import DEFAULT_RULES


def _get_base_path() -> str:
    """获取数据文件基础路径"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DataStorage:
    """统一的数据存储管理类"""

    def __init__(self, base_path: str | None = None):
        self.base_path = base_path or _get_base_path()
        self.rules_file = os.path.join(self.base_path, "rules.json")
        self.users_file = os.path.join(self.base_path, "users.json")
        self.history_file = os.path.join(self.base_path, "inference_history.json")

    def _load_json(self, filepath: str, default=None):
        """加载 JSON 文件"""
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default if default is not None else {}

    def _save_json(self, filepath: str, data):
        """保存 JSON 文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ========== 规则管理 ==========

    def load_rules(self) -> list[tuple[list[str], str]]:
        """加载规则"""
        data = self._load_json(self.rules_file, {"rules": []})
        rules = data.get("rules", [])
        if not rules:
            rules = [[list(pres), ans] for pres, ans in DEFAULT_RULES]
            self.save_rules([(pres, ans) for pres, ans in rules])
        return [(pres, ans) for pres, ans in rules]

    def save_rules(self, rules: list[tuple[list[str], str]]):
        """保存规则"""
        self._save_json(
            self.rules_file, {"rules": [[pres, ans] for pres, ans in rules]}
        )

    # ========== 用户管理 ==========

    def load_users(self) -> dict:
        """加载用户数据"""
        data = self._load_json(self.users_file, {"users": {}})
        # 确保有默认管理员
        if "admin" not in data.get("users", {}):
            data["users"] = data.get("users", {})
            data["users"]["admin"] = {
                "password": "admin123",
                "role": "admin",
                "created_at": datetime.now().isoformat(),
            }
            self._save_json(self.users_file, data)
        return data

    def save_users(self, data: dict):
        """保存用户数据"""
        self._save_json(self.users_file, data)

    # ========== 历史记录管理 ==========

    def load_history(self) -> list:
        """加载推理历史"""
        data = self._load_json(self.history_file, {"history": []})
        return data.get("history", [])

    def save_history(self, history: list):
        """保存推理历史"""
        # 只保留最近1000条
        if len(history) > 1000:
            history = history[-1000:]
        self._save_json(self.history_file, {"history": history})

    def add_history(self, record: dict):
        """添加历史记录"""
        history = self.load_history()
        history.append(record)
        self.save_history(history)
