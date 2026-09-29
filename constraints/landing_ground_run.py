"""着陆滑跑距离约束（翼载上限）。

**公式出处**：刘虎 等《飞机总体设计》第 3 章 3.3 节，式(3.29)~(3.34)，印刷页 42。

推导要点（主管方程取 ``dh/dt = 0``，并假定 ``F ≪ (D+R)``、阻力以地面摩擦为主
``(D+R) ≈ μ·mg``）：

    -μ = (1/g)·dV/dt          (3.29)
    x_LGR = V_TD²/(2μg)       (3.31)
    V_TD = k_TD·V_s           (3.32)

将失速速度代入并整理，得着陆滑跑距离约束方程：

    (m0/S) = x_LGR·ρ·C_Lmax·μ / (k_TD²·β)            (3.34)

本式只含翼载、与推重比无关，因此是一条**竖直边界**（``sense = "<="``）。

**李为吉版 2.4 节未给出着陆约束**，本模型是对模型库的补充。
"""

from __future__ import annotations

import numpy as np

from core.units import G0, isa_density

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="landing_ground_run",
        name_cn="着陆滑跑距离约束",
        category="着陆",
        sense="<=",
        kind=ConstraintKind.VERTICAL,
        requires=(
            "landing_ground_run",
            "cl_max_landing",
            "landing_friction_mu",
            "touchdown_speed_factor",
            "beta_landing",
        ),
        reference="刘虎《飞机总体设计》3.3 节 式(3.34)，印刷页 42",
    )
)
def compute(params, ws: np.ndarray) -> float:
    """返回满足着陆滑跑距离要求所允许的最大翼载。

    Args:
        params: 总设参数对象。
        ws: 翼载数组（本约束不使用）。

    Returns:
        允许的最大 W/S，N/m²，标量。
    """
    if params.cl_max_landing <= 0.0:
        raise ValueError("着陆滑跑距离约束：cl_max_landing 必须为正")
    if params.touchdown_speed_factor <= 0.0:
        raise ValueError("着陆滑跑距离约束：touchdown_speed_factor 必须为正")
    if params.landing_friction_mu <= 0.0:
        raise ValueError("着陆滑跑距离约束：landing_friction_mu 必须为正")
    if params.beta_landing <= 0.0:
        raise ValueError("着陆滑跑距离约束：beta_landing 必须为正")

    # 着陆按海平面标准大气计算
    density = float(isa_density(0.0))

    # 式(3.34)：m0/S = x·ρ·C_Lmax·μ/(k_TD²·β)，单位 kg/m²
    wing_loading_kg = (
        params.landing_ground_run
        * density
        * params.cl_max_landing
        * params.landing_friction_mu
        / (params.touchdown_speed_factor**2 * params.beta_landing)
    )

    # kg/m² → N/m²（本项目内部统一用 N/m²）
    return float(wing_loading_kg * G0)
