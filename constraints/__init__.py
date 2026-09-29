"""约束曲线模型库（插件目录）。

往本目录放一个用 `@register_constraint` 装饰的模型文件即可被自动发现，
无需改动其他任何代码。完整流程见 `.github/skills/add-constraint-model/SKILL.md`。
"""

from .base import (
    REGISTRY,
    ConstraintKind,
    ConstraintMeta,
    RegisteredConstraint,
    Sense,
    register_constraint,
)
from .registry import (
    clear_registry,
    discover_constraints,
    get_constraint,
    list_constraints,
)

__all__ = [
    "REGISTRY",
    "ConstraintKind",
    "ConstraintMeta",
    "RegisteredConstraint",
    "Sense",
    "clear_registry",
    "discover_constraints",
    "get_constraint",
    "list_constraints",
    "register_constraint",
]
