"""约束模型的接口契约。

新增一个约束 = 在 `constraints/` 下放一个文件，用 `@register_constraint` 装饰一个
签名固定的函数。目录由 `constraints.registry.discover_constraints()` 自动扫描，
不需要改动任何其他代码。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, TypeVar

import numpy as np

F = TypeVar("F", bound=Callable[..., Any])


class ConstraintKind(str, Enum):
    """约束在 W/S - T/W 平面上的几何形态。"""

    CURVE = "curve"            # y = f(x)：T/W 随翼载变化
    VERTICAL = "vertical"      # x = const：纯翼载限值
    HORIZONTAL = "horizontal"  # y = const：纯推重比下限


class Sense(str, Enum):
    """可行半平面位于曲线的哪一侧。

    方向写反会让可行域完全错误，而图看起来仍然"正常"，极难发现 —— 头号易错点。
    """

    GE = ">="  # 曲线（含）上方可行
    LE = "<="  # 曲线（含）下方可行


_KINDS: dict[str, ConstraintKind] = {k.value: k for k in ConstraintKind}
_SENSES: dict[str, Sense] = {s.value: s for s in Sense}


@dataclass(frozen=True)
class ConstraintMeta:
    """约束元数据，由每个模型文件在注册时声明。"""

    key: str                          # 唯一标识，应与文件名一致（snake_case）
    name_cn: str                      # 中文名，出现在图例上
    category: str                     # 分类：起飞 / 着陆 / 爬升 / 巡航 / 机动 / 限制
    sense: Sense | str                # 可行域在曲线的哪一侧
    kind: ConstraintKind | str        # 曲线形态
    requires: tuple[str, ...] = ()    # 依赖的 DesignParams 字段名，供缺参预检
    reference: str = ""               # 公式出处（书名 + 章节/页码），必须非空

    def __post_init__(self) -> None:
        if isinstance(self.sense, str):
            try:
                object.__setattr__(self, "sense", _SENSES[self.sense])
            except KeyError:
                raise ValueError(
                    f"约束 {self.key!r} 的 sense={self.sense!r} 非法，只能是 '>=' 或 '<='"
                ) from None

        if isinstance(self.kind, str):
            try:
                object.__setattr__(self, "kind", _KINDS[self.kind])
            except KeyError:
                raise ValueError(
                    f"约束 {self.key!r} 的 kind={self.kind!r} 非法，"
                    f"只能是 {sorted(_KINDS)} 之一"
                ) from None

        if not self.reference:
            raise ValueError(
                f"约束 {self.key!r} 缺少 reference —— 公式必须可溯源，"
                "请填写书名与章节/页码"
            )

        object.__setattr__(self, "requires", tuple(self.requires))


@dataclass(frozen=True)
class RegisteredConstraint:
    """注册表中的一条记录。"""

    meta: ConstraintMeta
    func: Callable[[Any, np.ndarray], np.ndarray | float]

    @property
    def key(self) -> str:
        return self.meta.key

    @property
    def requires(self) -> tuple[str, ...]:
        return self.meta.requires

    def __call__(self, params: Any, ws: np.ndarray) -> np.ndarray | float:
        return self.func(params, ws)


REGISTRY: dict[str, RegisteredConstraint] = {}
"""key -> 约束记录。由 @register_constraint 填充。"""


def register_constraint(meta: ConstraintMeta) -> Callable[[F], F]:
    """把模型函数登记进全局注册表。

    Args:
        meta: 约束元数据。

    Returns:
        装饰器，原样返回被装饰的函数。
    """
    if not isinstance(meta, ConstraintMeta):
        raise TypeError(
            f"register_constraint 需要 ConstraintMeta 实例，收到 {type(meta).__name__}"
        )

    def decorator(func: F) -> F:
        if meta.key in REGISTRY:
            other = REGISTRY[meta.key].func
            raise ValueError(
                f"约束 key {meta.key!r} 重复注册："
                f"{other.__module__} 与 {func.__module__} 冲突"
            )
        REGISTRY[meta.key] = RegisteredConstraint(meta=meta, func=func)
        return func

    return decorator
