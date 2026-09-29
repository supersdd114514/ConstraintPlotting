"""爬升率约束。

**公式出处**：刘虎 等《飞机总体设计》第 3 章 3.3 节，式(3.23)，印刷页 41
（主管方程 (3.15) 取 ``dV/dt = 0, n = 1, R = 0``）。

原式：

    F0/(m0 g) = (β/α)·{ K1·(βg/q)(m0/S) + K2
                         + C_D0/((βg/q)(m0/S)) + (1/V)·dh/dt }

**与李为吉 (2.24) 的关系 —— 已交叉验证**：

李为吉爬升梯度约束 ``T/W ≥ G + 2√(C_D0/(πAe))`` 是本式对 ``C_L`` 取极小的结果：

    min_{C_L} ( K1·C_L + C_D0/C_L ) = 2√(K1·C_D0) = 2√( C_D0/(πAe) )

即 **李为吉给的是最保守的水平下界，刘虎给的是指定速度下的真实曲线**。
两者分别对应“爬升梯度”与“爬升率”两类不同要求，因此本项目**同时保留**：
``climb_gradient``（水平线）与 ``climb_rate``（曲线）。
"""

from __future__ import annotations

import numpy as np

from core.aero import induced_drag_factor, required_thrust_weight
from core.units import dynamic_pressure, isa_density

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="climb_rate",
        name_cn="爬升率约束",
        category="爬升",
        sense=">=",
        kind=ConstraintKind.CURVE,
        requires=(
            "climb_rate",
            "climb_altitude",
            "climb_speed",
            "cd0_clean",
            "aspect_ratio",
            "oswald_e",
            "polar_k2",
            "beta_climb",
            "alpha_climb",
        ),
        reference="刘虎《飞机总体设计》3.3 节 式(3.23)，印刷页 41",
    )
)
def compute(params, ws: np.ndarray) -> np.ndarray:
    """给定翼载，返回达到规定爬升率所需的推重比下限。

    Args:
        params: 总设参数对象。
        ws: 翼载数组，N/m²。

    Returns:
        所需 T/W 数组。曲线呈碗形，极小值对应最佳爬升翼载。
    """
    density = float(isa_density(params.climb_altitude))
    q = float(dynamic_pressure(density, params.climb_speed))
    k1 = float(induced_drag_factor(params.aspect_ratio, params.oswald_e))

    return np.asarray(
        required_thrust_weight(
            wing_loading=ws,
            dynamic_pressure=q,
            cd0=params.cd0_clean,
            k1=k1,
            k2=params.polar_k2,
            load_factor=1.0,
            beta=params.beta_climb,
            alpha=params.alpha_climb,
            climb_rate=params.climb_rate,
            speed=params.climb_speed,
        )
    )
