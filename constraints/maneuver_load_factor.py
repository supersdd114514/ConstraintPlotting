"""机动过载约束（翼载上限）。

**公式出处**：李为吉《飞机总体设计》第 2 章 2.4 节，式(2.36)，印刷页 23。

原式：

    W/S = C_Lmax / n · ½ ρ V²              (2.36)

**形态**：与 T/W 无关，是一条**竖直边界**；``sense = "<="`` 表示翼载不得高于该值。

**注意**：书中特别提示 —— 由格斗重量得到的结果需再除以「格斗重量/起飞重量」
（多数飞机 ≈ 0.85）才是起飞翼载。本模型按**起飞重量口径**直接给出上限，
若参数中的过载对应格斗重量，请自行在 ``load_factor_maneuver`` 上折算。
"""

from __future__ import annotations

import numpy as np

from core.units import dynamic_pressure, isa_density

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="maneuver_load_factor",
        name_cn="机动过载约束",
        category="机动",
        sense="<=",
        kind=ConstraintKind.VERTICAL,
        requires=(
            "load_factor_maneuver",
            "cl_max_maneuver",
            "maneuver_speed",
            "altitude_maneuver",
        ),
        reference="李为吉《飞机总体设计》2.4 节 式(2.36)，印刷页 23",
    )
)
def compute(params, ws: np.ndarray) -> float:
    """返回在给定过载、速度与高度下所允许的最大翼载。

    Args:
        params: 总设参数对象。
        ws: 翼载数组（本约束不使用）。

    Returns:
        允许的最大 W/S，N/m²，标量。
    """
    if params.load_factor_maneuver <= 0.0:
        raise ValueError("机动过载约束：load_factor_maneuver 必须为正")
    if params.cl_max_maneuver < 0.0:
        raise ValueError("机动过载约束：cl_max_maneuver 不能为负")

    density = float(isa_density(params.altitude_maneuver))
    q = float(dynamic_pressure(density, params.maneuver_speed))

    return float(params.cl_max_maneuver / params.load_factor_maneuver * q)
