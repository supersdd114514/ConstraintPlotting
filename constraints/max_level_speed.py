"""最大平飞速度约束。

**公式出处**

- 刘虎 等《飞机总体设计》第 3 章 3.3 节，式(3.24)，印刷页 41
  （主管方程 (3.15) 取 ``dh/dt = 0, dV/dt = 0, n = 1, R = 0``）
- 李为吉《飞机总体设计》第 2 章 2.4 节，式(2.31)，印刷页 21

原式（刘虎 3.24）：

    F0/(m0 g) = (β/α)·{ K1·(βg/q)(m0/S) + K2 + C_D0/((βg/q)(m0/S)) }

**两书公式等价 —— 已交叉验证**：把完整极曲线 ``C_D = C_D0 + K1·C_L²``（K2=0）
代入李为吉式(2.31)的 ``T/W = ½ρV²·C_D/(W/S)``，令 ``w = W/S``、``C_L = w/q``：

    D/W = q·C_D/w = q·C_D0/w + K1·w/q

正是刘虎式(3.24)。差别仅在于李为吉把 ``C_D`` 写成了一个代数量。

**本模型采用刘虎的分离写法**（显式区分 C_D0 与诱导阻力），因此曲线存在
**特征极小值**（对应最佳翼载），而合并写法会退化成单调递减的双曲线。

**α 的影响**：推力比 ``alpha_max_speed`` 把高速巡航时的推力衰减计入，
使所需起飞推重比显著高于瞬时需用值（高速时安装推力远小于海平面静推力）。
"""

from __future__ import annotations

import numpy as np

from core.aero import induced_drag_factor, required_thrust_weight
from core.units import dynamic_pressure, isa_density

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="max_level_speed",
        name_cn="最大平飞速度约束",
        category="速度",
        sense=">=",
        kind=ConstraintKind.CURVE,
        requires=(
            "max_level_speed",
            "altitude_max_speed",
            "cd0_clean",
            "aspect_ratio",
            "oswald_e",
            "polar_k2",
            "beta_max_speed",
            "alpha_max_speed",
        ),
        reference="刘虎《飞机总体设计》3.3 节 式(3.24)，印刷页 41；亦见李为吉 2.4 节 式(2.31)，印刷页 21",
    )
)
def compute(params, ws: np.ndarray) -> np.ndarray:
    """给定翼载，返回达到最大平飞速度所需的推重比下限。

    Args:
        params: 总设参数对象。
        ws: 翼载数组，N/m²。

    Returns:
        所需 T/W 数组。曲线呈碗形，极小值对应最省推力的翼载。
    """
    density = float(isa_density(params.altitude_max_speed))
    q = float(dynamic_pressure(density, params.max_level_speed))
    k1 = float(induced_drag_factor(params.aspect_ratio, params.oswald_e))

    return np.asarray(
        required_thrust_weight(
            wing_loading=ws,
            dynamic_pressure=q,
            cd0=params.cd0_clean,
            k1=k1,
            k2=params.polar_k2,
            load_factor=1.0,
            beta=params.beta_max_speed,
            alpha=params.alpha_max_speed,
        )
    )
