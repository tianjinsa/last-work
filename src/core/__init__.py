try:
    # 优先使用包内的cpp编译扩展（如果存在且 ABI 匹配）
    from .Rule_reasoner import Rule_reasoner as RuleReasoner
except (ImportError, ModuleNotFoundError, AttributeError):
    # 回退到纯 Python 实现
    from .reasoner import RuleReasoner
    print("警告: 未能加载编译扩展，已回退到纯 Python 实现的推理引擎。")
# from .reasoner import RuleReasoner

__all__ = ["RuleReasoner"]
