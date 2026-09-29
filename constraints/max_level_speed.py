"""最大平飞速度约束。

**公式出处**：李为吉《飞机总体设计》第 2 章 2.4 节，式(2.29)~(2.31)，印刷页 21。

原式：

    T/W = ½ ρ v_max² C_D / (W/S)          (2.31)

其中由 ``v_max = √(2(T/W)(W/S)/(ρ C_D))``  (2.30) 反解而来。

**注意**：这是书中给出的**简化形式** —— 阻力系数 C_D 取单一值（由参数
``cd_max_level_speed`` 提供），未显式拆分零升阻力与诱导阻力。若需要更精细的
极曲线形式，应另建模型并注明推导出处。

曲线形态：对 W/S **单调递减** —— 翼载越大意味着同样总重下机翼越小、高速阻力越小。
"""

from __future__ import annotations

import numpy as np

from core.numeric import ignore_divide_warnings
from core.units import dynamic_pressure, isa_density

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="max_level_speed",
        name_cn="最大平飞速度约束",
        category="速度",
        sense=">=",
        kind=ConstraintKind.CURVE,
        requires=("max_level_speed", "altitude_max_speed", "cd_max_level_speed"),
        reference="李为吉《飞机总体设计》2.4 节 式(2.31)，印刷页 21",
    )
)
def compute(params, ws: np.ndarray) -> np.ndarray:
    """给定翼载，返回达到最大平飞速度所需的推重比下限。

    Args:
        params: 总设参数对象。
        ws: 翼载数组，N/m²。

    Returns:
        所需 T/W 数组。W/S → 0 时发散（``+inf``），由 `core.analyzer` 截断处理。
    """
    density = float(isa_density(params.altitude_max_speed))
    q = float(dynamic_pressure(density, params.max_level_speed))

    ws = np.asarray(ws, dtype=float)
    with ignore_divide_warnings():
        return q * params.cd_max_level_speed / ws
