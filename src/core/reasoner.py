"""
推理引擎 - 纯 Python 实现
支持正向推理和反向推理
"""

from typing import Optional


class RuleReasoner:
    """推理器类"""

    def __init__(self) -> None:
        """构造后需通过 reset 提供规则"""
        self._lines_list: list[tuple[list[int], int]] = (
            []
        )  # 储存所有规则 (前提id列表, 结论id)
        self._node_list: list[dict] = (
            []
        )  # 储存所有节点 {prelines_id: [], anslines_id: []}
        self._name_id_map: dict[str, int] = {}  # 根据name找node_id
        self._id_name_map: dict[int, str] = {}  # 根据id找name
        self._known_set: set[int] = set()  # 已知信息集合
        self._reasoner_path: list[int] = []  # 推理路径，储存经过的line_id
        self._reasoner_set: set[int] = set()  # 经过的line_id集合

        # 反向推理状态
        self._bw_stack: list[dict] = []  # 反向推理栈 [{u: int, rule_idx: int}]
        self._false_set: set[int] = set()  # 已知为假的事实
        self._in_backward: int = -1  # 当前反向推理目标

    def _get_line_id(self, pres_id: list[int], ans_id: int) -> int:
        """插入规则并获得id"""
        self._lines_list.append((pres_id, ans_id))
        return len(self._lines_list) - 1

    def _get_name_id(self, name: str) -> int:
        """插入name并获得id"""
        if name in self._name_id_map:
            return self._name_id_map[name]

        node_id = len(self._name_id_map)
        self._name_id_map[name] = node_id
        self._id_name_map[node_id] = name
        self._node_list.append({"prelines_id": [], "anslines_id": []})
        return node_id

    def _get_id_name(self, node_id: int) -> str:
        """根据id找name"""
        return self._id_name_map[node_id]

    def _add_rule(self, pres: list[str], ans: str) -> None:
        """添加单条规则"""
        pres_id = [self._get_name_id(p) for p in pres]
        ans_id = self._get_name_id(ans)
        line_id = self._get_line_id(pres_id, ans_id)

        # 更新节点的规则引用
        for pre_id in pres_id:
            self._node_list[pre_id]["anslines_id"].append(line_id)
        self._node_list[ans_id]["prelines_id"].append(line_id)

    def reset(self, rules: list[tuple[list[str], str]]) -> None:
        """重置推理器"""
        self._lines_list.clear()
        self._node_list.clear()
        self._name_id_map.clear()
        self._id_name_map.clear()
        self._known_set.clear()
        self._reasoner_path.clear()
        self._reasoner_set.clear()
        self._false_set.clear()
        self._bw_stack.clear()
        self._in_backward = -1

        for pres, ans in rules:
            self._add_rule(pres, ans)

    def add_known(self, known: list[str]) -> None:
        """添加已知信息"""
        for k in known:
            self._known_set.add(self._get_name_id(k))

    def clear_known(self) -> None:
        """清空已知信息"""
        self._known_set.clear()
        self._reasoner_path.clear()

    def add_false(self, falses: list[str]) -> None:
        """添加反例信息"""
        for f in falses:
            self._false_set.add(self._get_name_id(f))

    def clear_false(self) -> None:
        """清空反例信息"""
        self._false_set.clear()

    def find(self) -> tuple[list[str], list[int]]:
        """开始正向推理，返回 (结论名字列表, 规则id路径)"""
        result: list[str] = []
        self._reasoner_path.clear()

        stack = list(self._known_set)

        while stack:
            now_id = stack.pop()
            now_node = self._node_list[now_id]

            # 如果没有后续规则，说明推理到尽头
            if not now_node["anslines_id"]:
                result.append(self._get_id_name(now_id))
                continue

            for line_id in now_node["anslines_id"]:
                pres_id, ans_id = self._lines_list[line_id]

                # 已经知道的结论就不推理了
                if ans_id in self._known_set:
                    continue

                # 检查所有前提是否满足
                can_get = all(pre_id in self._known_set for pre_id in pres_id)

                if can_get:
                    self._reasoner_path.append(line_id)
                    self._known_set.add(ans_id)
                    stack.append(ans_id)

        return result, self._reasoner_path.copy()

    def step_backward(self, target: str) -> tuple[int, list[str], list[int]]:
        """
        反向推理单步执行
        返回: (状态, 数据, 路径)
        - 状态 0: 成功, 数据为目标名字
        - 状态 1: 失败, 数据为空
        - 状态 2: 询问, 数据为需要确认的事实名字列表
        """
        target_id = self._get_name_id(target)
        self._reasoner_path.clear()
        self._reasoner_set.clear()

        # 如果目标改变，重置栈
        if self._in_backward != target_id:
            self._bw_stack.clear()
            self._bw_stack.append({"u": target_id, "rule_idx": 0})
            self._in_backward = target_id

        while self._bw_stack:
            top = self._bw_stack[-1]
            u = top["u"]

            # 如果已知为真，弹出
            if u in self._known_set:
                self._bw_stack.pop()
                continue

            # 如果已知为假，弹出
            if u in self._false_set:
                self._bw_stack.pop()
                continue

            rules = self._node_list[u]["prelines_id"]

            # 所有规则都尝试过了，标记为假
            if top["rule_idx"] >= len(rules):
                self._false_set.add(u)
                self._bw_stack.pop()
                continue

            line_id = rules[top["rule_idx"]]
            pres_id, _ = self._lines_list[line_id]

            rule_possible = True
            subgoal: Optional[int] = None
            to_ask: list[str] = []

            for pre_id in pres_id:
                # 如果前提已知为假，规则不可行
                if pre_id in self._false_set:
                    rule_possible = False
                    break

                # 如果前提已知为真，跳过
                if pre_id in self._known_set:
                    continue

                # 如果前提没有推导规则，需要询问用户
                if not self._node_list[pre_id]["prelines_id"]:
                    to_ask.append(self._get_id_name(pre_id))
                else:
                    # 有推导规则，设为子目标
                    if subgoal is None:
                        subgoal = pre_id

            # 规则不可行，尝试下一条规则
            if not rule_possible:
                top["rule_idx"] += 1
                continue

            # 有子目标需要先证明
            if subgoal is not None:
                self._bw_stack.append({"u": subgoal, "rule_idx": 0})
                continue

            # 需要询问用户
            if to_ask:
                return 2, to_ask, self._reasoner_path.copy()

            # 所有前提满足，目标成立
            self._known_set.add(u)
            if line_id not in self._reasoner_set:
                self._reasoner_path.append(line_id)
                self._reasoner_set.add(line_id)
            self._bw_stack.pop()

        self._in_backward = -1

        if target_id in self._known_set:
            return 0, [target], self._reasoner_path.copy()
        return 1, [], self._reasoner_path.copy()
