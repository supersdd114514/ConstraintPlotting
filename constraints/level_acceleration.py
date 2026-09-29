"""水平加减速约束。

**公式出处**：刘虎 等《飞机总体设计》第 3 章 3.3 节，式(3.25)~(3.26)，印刷页 41。

原式（主管方程 (3.15) 取 ``dh/dt = 0, R = 0, n = 1``）：

    F0/(m0 g) = (β/α)·{ K1·(βg/q)(m0/S) + K2
                         + C_D0/((βg/q)(m0/S)) + (1/g)·dV/dt }

加速度按允许时间简化（式 3.26）：

    dV/dt = |V_终止 - V_起始| / Δt_允许

本约束考核的是「从 V_起始 加速到 V_终止 所需时间不超过 Δt」这一要求。
"""

from __future__ import annotations

import numpy as np

from core.aero import induced_drag_factor, required_thrust_weight
from core.units import dynamic_pressure, isa_density

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="level_acceleration",
        name_cn="水平加减速约束",
        category="加速性",
        sense=">=",
        kind=ConstraintKind.CURVE,
        requires=(
            "acceleration_speed_initial",
            "acceleration_speed_final",
            "acceleration_allowable_time",
            "acceleration_altitude",
            "cd0_clean",
            "aspect_ratio",
            "oswald_e",
            "polar_k2",
            "beta_acceleration",
            "alpha_acceleration",
        ),
        reference="刘虎《飞机总体设计》3.3 节 式(3.25)(3.26)，印刷页 41",
    )
)
def compute(params, ws: np.ndarray) -> np.ndarray:
    """给定翼载，返回满足加减速时间要求所需的推重比下限。

    Args:
        params: 总设参数对象。
        ws: 翼载数组，N/m²。

    Returns:
        所需 T/W 数组。动压按起止速度的**平均值**取。
    """
    if params.acceleration_allowable_time <= 0.0:
        raise ValueError("水平加减速约束：acceleration_allowable_time 必须为正")

    speed_mean = 0.5 * (
        params.acceleration_speed_initial + params.acceleration_speed_final
    )
    density = float(isa_density(params.acceleration_altitude))
    q = float(dynamic_pressure(density, speed_mean))

    acceleration = (
        abs(params.acceleration_speed_final - params.acceleration_speed_initial)
        / params.acceleration_allowable_time
    )
    k1 = float(induced_drag_factor(params.aspect_ratio, params.oswald_e))

    return np.asarray(
        required_thrust_weight(
            wing_loading=ws,
            dynamic_pressure=q,
            cd0=params.cd0_clean,
            k1=k1,
            k2=params.polar_k2,
            load_factor=1.0,
            beta=params.beta_acceleration,
            alpha=params.alpha_acceleration,
            acceleration=acceleration,
        )
    )
