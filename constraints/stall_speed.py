"""失速速度约束（翼载上限）。

**公式出处**：李为吉《飞机总体设计》第 2 章 2.4 节，式(2.32)~(2.33)，印刷页 22。

原式：

    W = L = ½ ρ V_S² S C_Lmax              (2.32)
    W/S = ½ ρ V_S² C_Lmax                  (2.33)

**形态**：与 T/W 无关，是一条**竖直边界**；``sense = "<="`` 表示翼载不得高于该值
（翼载越大，同样失速速度下需要越大升力系数，超出可用范围即不安全）。
"""

from __future__ import annotations

import numpy as np

from core.units import isa_density

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="stall_speed",
        name_cn="失速速度约束",
        category="限制",
        sense="<=",
        kind=ConstraintKind.VERTICAL,
        requires=("stall_speed", "cl_max_landing", "altitude_stall"),
        reference="李为吉《飞机总体设计》2.4 节 式(2.33)，印刷页 22",
    )
)
def compute(params, ws: np.ndarray) -> float:
    """返回满足失速速度要求所允许的最大翼载。

    Args:
        params: 总设参数对象。
        ws: 翼载数组（本约束不使用）。

    Returns:
        允许的最大 W/S，N/m²，标量。
    """
    if params.stall_speed <= 0.0 or params.cl_max_landing <= 0.0:
        raise ValueError("失速速度约束：stall_speed 与 cl_max_landing 必须为正")

    density = float(isa_density(params.altitude_stall))
    return float(0.5 * density * params.stall_speed**2 * params.cl_max_landing)
