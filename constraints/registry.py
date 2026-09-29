"""注册表查询与模型目录自动发现。

`discover_constraints()` 扫描 `constraints/` 目录并导入其中所有模型模块，
这是「新增约束无需改动其他代码」的实现基础。
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from .base import REGISTRY, RegisteredConstraint

# 非模型模块，扫描时跳过
_SKIP: frozenset[str] = frozenset({"base", "registry"})

_PKG_DIR = Path(__file__).resolve().parent
_PKG_NAME = __package__ or "constraints"

_discovered = False


def discover_constraints(force: bool = False) -> list[RegisteredConstraint]:
    """扫描 `constraints/` 目录，导入其中所有模型模块。

    遇到 import 失败**直接抛出**，绝不静默跳过 —— 静默失败会让约束悄悄不生效，
    而图上看不出任何异常，是最难排查的故障模式。

    Args:
        force: 为 True 时即使已扫描过也重新导入。

    Returns:
        全部已注册约束，按 key 排序。

    Raises:
        ImportError: 任一模型模块导入失败时原样抛出。
    """
    global _discovered
    if _discovered and not force:
        return list_constraints()

    for mod in pkgutil.iter_modules([str(_PKG_DIR)]):
        if mod.name in _SKIP or mod.name.startswith("_"):
            continue
        # 故意不包 try/except：导入失败必须让调用方立刻看到
        importlib.import_module(f"{_PKG_NAME}.{mod.name}")

    _discovered = True
    return list_constraints()


def list_constraints() -> list[RegisteredConstraint]:
    """按 key 排序返回全部已注册约束。"""
    return [REGISTRY[key] for key in sorted(REGISTRY)]


def get_constraint(key: str) -> RegisteredConstraint:
    """按 key 取单个约束。

    Raises:
        KeyError: key 未注册，附带可用 key 列表。
    """
    try:
        return REGISTRY[key]
    except KeyError:
        raise KeyError(
            f"约束 {key!r} 未注册。已注册：{sorted(REGISTRY) or '（无）'}"
        ) from None


def clear_registry() -> None:
    """清空注册表并复位发现标志。仅供测试使用。"""
    global _discovered
    REGISTRY.clear()
    _discovered = False
