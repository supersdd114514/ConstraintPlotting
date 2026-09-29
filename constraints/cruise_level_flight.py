"""巡航平飞约束。

**公式出处**：李为吉《飞机总体设计》第 2 章 2.4 节，式(2.23)，印刷页 18。

原式：

    (T/W)_巡航 = 1 / (L/D)_巡航            (2.23)

飞机在巡航状态作水平匀速飞行时，升力等于重量、推力等于阻力，故推重比等于
升阻比的倒数。

**形态**：与 W/S 无关，是一条**水平线**。这是各约束中通常最松的一条。
"""

from __future__ import annotations

import numpy as np

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="cruise_level_flight",
        name_cn="巡航平飞约束",
        category="巡航",
        sense=">=",
        kind=ConstraintKind.HORIZONTAL,
        requires=("ld_cruise",),
        reference="李为吉《飞机总体设计》2.4 节 式(2.23)，印刷页 18",
    )
)
def compute(params, ws: np.ndarray) -> float:
    """返回维持巡航平飞所需的推重比下限。

    Args:
        params: 总设参数对象。
        ws: 翼载数组（本约束不使用）。

    Returns:
        所需 T/W 下限，标量，等于巡航升阻比的倒数。
    """
    if params.ld_cruise <= 0.0:
        raise ValueError("巡航平飞约束：ld_cruise 必须为正")

    return float(1.0 / params.ld_cruise)
