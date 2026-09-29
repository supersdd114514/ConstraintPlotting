"""爬升梯度约束。

**公式出处**：李为吉《飞机总体设计》第 2 章 2.4 节，式(2.24)，印刷页 19。

原式：

    T/W ≥ G + 2·√( C_D0 / (π A e) )        (2.24)

式中 G 为爬升梯度，C_D0 为零升阻力系数，A 为展弦比，e 为奥斯瓦尔德效率因子。

**形态**：与 W/S 无关，因此在 W/S–T/W 平面上是一条**水平线**。
"""

from __future__ import annotations

import numpy as np

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="climb_gradient",
        name_cn="爬升梯度约束",
        category="爬升",
        sense=">=",
        kind=ConstraintKind.HORIZONTAL,
        requires=("climb_gradient", "cd0_clean", "aspect_ratio", "oswald_e"),
        reference="李为吉《飞机总体设计》2.4 节 式(2.24)，印刷页 19",
    )
)
def compute(params, ws: np.ndarray) -> float:
    """返回满足爬升梯度要求所需的推重比下限（与翼载无关）。

    Args:
        params: 总设参数对象。
        ws: 翼载数组（本约束不使用）。

    Returns:
        所需 T/W 下限，标量。
    """
    denominator = np.pi * params.aspect_ratio * params.oswald_e
    if params.cd0_clean < 0.0 or denominator <= 0.0:
        raise ValueError(
            "爬升梯度约束：cd0_clean 必须非负，aspect_ratio 与 oswald_e 必须为正"
        )

    return float(params.climb_gradient + 2.0 * np.sqrt(params.cd0_clean / denominator))
