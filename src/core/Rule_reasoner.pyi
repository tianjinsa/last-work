from __future__ import annotations
import collections.abc
__all__: list[str] = ['Rule_reasoner']
class Rule_reasoner:
    """
    推理器类
    """
    def __init__(self) -> None:
        """
        构造后需通过 reset 提供规则
        """
    def add_false(self, falses: list[str]) -> None:
        """
        添加反例信息
        """
    def add_known(self, known: list[str]) -> None:
        """
        添加已知信息
        """
    def clear_false(self) -> None:
        """
        清空反例信息
        """
    def clear_known(self) -> None:
        """
        清空已知信息
        """
    def find(self) -> tuple[list[str], list[int]]:
        """
        开始推理，返回名字而非id
        """
    def reset(self, rules: list[tuple[list[str], str]]) -> None:
        """
        重置推理器
        """
    def step_backward(self, target: str) -> tuple[int, list[str], list[int]]:
        """
        返回: 状态 (0: 成功, 1: 失败, 2: 询问), 数据 (名字或名字列表), 路径 (规则id列表)
        """
