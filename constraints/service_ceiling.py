"""升限约束（翼载上限）。

**公式出处**：李为吉《飞机总体设计》第 2 章 2.4 节，式(2.37)，印刷页 24。

原式：

    W/S = ½ ρ_H · v_a² · C_L               (2.37)

式中 ρ_H 为升限高度的空气密度，v_a 为可用推力最大时的飞行速度，C_L 为升限
飞行时的升力系数。

**形态**：与 T/W 无关，是一条**竖直边界**；``sense = "<="`` 表示翼载不得高于该值。
"""

from __future__ import annotations

import numpy as np

from core.units import isa_density

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="service_ceiling",
        name_cn="升限约束",
        category="限制",
        sense="<=",
        kind=ConstraintKind.VERTICAL,
        requires=("ceiling_altitude", "ceiling_speed", "cl_ceiling"),
        reference="李为吉《飞机总体设计》2.4 节 式(2.37)，印刷页 24",
    )
)
def compute(params, ws: np.ndarray) -> float:
    """返回满足升限要求所允许的最大翼载。

    Args:
        params: 总设参数对象。
        ws: 翼载数组（本约束不使用）。

    Returns:
        允许的最大 W/S，N/m²，标量。
    """
    if params.cl_ceiling <= 0.0:
        raise ValueError("升限约束：cl_ceiling 必须为正")

    density = float(isa_density(params.ceiling_altitude))
    return float(0.5 * density * params.ceiling_speed**2 * params.cl_ceiling)
