"""数值保护工具。

约束曲线在 W/S → 0 或速度项 → 0 时会发散出 inf/nan。若不处理，matplotlib 的
自动坐标范围会被拉飞，整张图不可读 —— 见 AGENTS.md「常见陷阱」。
"""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

import numpy as np


@contextmanager
def ignore_divide_warnings() -> Iterator[None]:
    """抑制除零/无效值告警（结果仍会是 inf/nan，需配合 sanitize_curve 使用）。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        yield


def sanitize_curve(y: np.ndarray, y_max: float) -> np.ndarray:
    """把曲线值清理到 ``[0, y_max]`` 内，供绘图与求交使用。

    处理策略（**不可混淆**）：

    - ``+inf`` → ``y_max``：公式发散说明该处需求超出任何合理推重比，
      截断到上限即可 —— 绘图窗口内该区域自然被判为不可行。
    - ``-inf`` → ``0.0``：同理，向另一侧发散。
    - ``nan``  → **原样保留**：公式在该点**无定义**，不能假装它"不构成限制"。
      由 `core.analyzer` 将其判定为不可行，避免用错误数据"造出"可行域。

    Args:
        y: 原始曲线值。
        y_max: 物理上合理的推重比上限，用于截断。

    Returns:
        与 ``y`` 同形状的数组，可能仍含 ``nan``。
    """
    arr = np.asarray(y, dtype=float)
    return np.clip(arr, 0.0, y_max)


def sanitize_bound(value: float, upper: float) -> float:
    """标量限值的清理，用于 vertical / horizontal 约束。

    与 `sanitize_curve` 不同，这里的 ``nan`` 同样保留，交由分析层判定不可行。
    """
    arr = np.asarray(value, dtype=float)
    return float(np.clip(arr, 0.0, upper))
