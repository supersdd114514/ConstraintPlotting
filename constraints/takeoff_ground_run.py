"""起飞滑跑距离约束。

**公式出处**：李为吉《飞机总体设计》第 2 章 2.4 节，式(2.27)，印刷页 20。

原式（书中 W/S 单位为 9.8 N/m²，即 kgf/m²）：

    T/W = 1.05 · [ 1.2/(C_LmaxTO · L_TOG) · (W/S) + ½(3μ_G + 1/(L/D)) ]

**单位换算说明**：系数 1.2 是配合 kgf/m² 标定的 —— 由式(2.25)的
``v_TO² = 23.6·(W/S)/C_LmaxTO``（W/S 取 kgf/m²）与 ``23.6/(2g) ≈ 1.2``（g 取 9.8）
得到。本项目内部统一使用 N/m²，因此代入前先除以 g，等价于把系数写成
``1.2/(g · C_LmaxTO · L_TOG)``。
"""

from __future__ import annotations

import numpy as np

from core.units import wing_loading_n_to_kg

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="takeoff_ground_run",
        name_cn="起飞滑跑距离约束",
        category="起飞",
        sense=">=",
        kind=ConstraintKind.CURVE,
        requires=(
            "cl_max_takeoff",
            "takeoff_ground_run",
            "ground_friction_mu",
            "ld_takeoff",
        ),
        reference="李为吉《飞机总体设计》2.4 节 式(2.27)，印刷页 20",
    )
)
def compute(params, ws: np.ndarray) -> np.ndarray:
    """给定翼载，返回满足给定滑跑距离所需的推重比下限。

    Args:
        params: 总设参数对象。
        ws: 翼载数组，N/m²。

    Returns:
        所需 T/W 数组。曲线对 W/S 单调递增 —— 翼载越大，同样距离内越难离地。
    """
    if params.cl_max_takeoff <= 0.0 or params.takeoff_ground_run <= 0.0:
        raise ValueError(
            "起飞滑跑距离约束：cl_max_takeoff 与 takeoff_ground_run 必须为正"
        )
    if params.ld_takeoff <= 0.0:
        raise ValueError("起飞滑跑距离约束：ld_takeoff 必须为正")

    ws_kgf = wing_loading_n_to_kg(np.asarray(ws, dtype=float))

    coefficient = 1.2 / (params.cl_max_takeoff * params.takeoff_ground_run)
    lift_drag_term = 0.5 * (3.0 * params.ground_friction_mu + 1.0 / params.ld_takeoff)

    return 1.05 * (coefficient * ws_kgf + lift_drag_term)
