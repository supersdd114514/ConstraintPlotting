"""持续盘旋过载约束（推力限制）。

**公式出处**：刘虎 等《飞机总体设计》第 3 章 3.3 节，式(3.27)，印刷页 41。

原式（主管方程 (3.15) 取 ``P_s = 0``，即 ``dh/dt = dV/dt = 0，R = 0``）：

    F0/(m0 g) = (β/α)·{ K1·n²·(βg/q)(m0/S) + K2·n + C_D0/((βg/q)(m0/S)) }

持续盘旋指飞机盘旋时不允许减速或损失高度：推力等于阻力，升力等于 n·mg。

**与 ``maneuver_load_factor``（李为吉 式 2.36）的区别 —— 两者互补，不可替代**：

====================== ========================================== ============
约束                    物理含义                                     形态
====================== ========================================== ============
``maneuver_load_factor`` **气动/升力限制**：翼载过大会导致在给定速度下  ``vertical``
                        无法产生 n 倍升力（李为吉 2.36）             W/S ≤ …
``sustained_turn``      **推力限制**：推重比不足则克服不了 n 倍过载  ``curve``
                        下的阻力（刘虎 3.27）                       T/W ≥ f(W/S)
====================== ========================================== ============

一个管“机翼够不够大”，一个管“发动机够不够强”，必须同时满足。
"""

from __future__ import annotations

import numpy as np

from core.aero import induced_drag_factor, required_thrust_weight
from core.units import dynamic_pressure, isa_density

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="sustained_turn",
        name_cn="持续盘旋过载约束",
        category="机动",
        sense=">=",
        kind=ConstraintKind.CURVE,
        requires=(
            "load_factor_maneuver",
            "maneuver_speed",
            "altitude_maneuver",
            "cd0_clean",
            "aspect_ratio",
            "oswald_e",
            "polar_k2",
            "beta_turn",
            "alpha_turn",
        ),
        reference="刘虎《飞机总体设计》3.3 节 式(3.27)，印刷页 41",
    )
)
def compute(params, ws: np.ndarray) -> np.ndarray:
    """给定翼载，返回维持 n 倍过载持续盘旋所需的推重比下限。

    Args:
        params: 总设参数对象。
        ws: 翼载数组，N/m²。

    Returns:
        所需 T/W 数组。过载越高、翼载越大，所需推力越大。
    """
    density = float(isa_density(params.altitude_maneuver))
    q = float(dynamic_pressure(density, params.maneuver_speed))
    k1 = float(induced_drag_factor(params.aspect_ratio, params.oswald_e))

    return np.asarray(
        required_thrust_weight(
            wing_loading=ws,
            dynamic_pressure=q,
            cd0=params.cd0_clean,
            k1=k1,
            k2=params.polar_k2,
            load_factor=params.load_factor_maneuver,
            beta=params.beta_turn,
            alpha=params.alpha_turn,
        )
    )
