"""缺参预检。

原则（见 AGENTS.md）：**宁可启动即报错，也不要跑出一张空图**。
约束模型通过 `ConstraintMeta.requires` 声明依赖的参数名，本模块在正式计算前
统一核对，并一次性列出全部缺失项，避免逐个试错。
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Sequence

from constraints.base import RegisteredConstraint


class MissingParameterError(ValueError):
    """约束依赖的参数在 DesignParams 中不存在。"""


def available_fields(params: Any) -> set[str]:
    """列出参数对象上可作为约束输入的字段名。"""
    if is_dataclass(params):
        return {f.name for f in fields(params)}
    return {name for name in dir(params) if not name.startswith("_")}


def missing_for(registered: RegisteredConstraint, params: Any) -> list[str]:
    """返回某条约束缺失的参数名。"""
    present = available_fields(params)
    return [name for name in registered.requires if name not in present]


def check_all(constraints: Sequence[RegisteredConstraint], params: Any) -> None:
    """核对全部约束的参数依赖，有问题则一次性抛出。

    Raises:
        MissingParameterError: 存在缺失参数，消息中列出每条约束缺什么。
    """
    problems: list[str] = []
    for registered in constraints:
        missing = missing_for(registered, params)
        if missing:
            problems.append(
                f"  - {registered.key}（{registered.meta.name_cn}）缺少："
                f"{', '.join(missing)}"
            )

    if problems:
        raise MissingParameterError(
            "以下约束依赖的参数未在参数对象中定义：\n"
            + "\n".join(problems)
            + "\n请在 config/params.py 中补齐（带单位注释），或调整该约束的 requires。"
        )
