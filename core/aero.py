"""气动系数与约束分析主管方程。

**公式出处**

- 刘虎 等《飞机总体设计》第 3 章 **3.3 节「约束分析」**，印刷页 39–46
  （PDF 页 = 印刷页 + 27）。
  - 主管方程 (3.15)、极曲线 (3.11)
  - 诱导阻力因子 K1 (3.35)、奥斯瓦尔德系数 (3.36)(3.37)
  - 推力比 α 估算 (3.38)~(3.44)
- 李为吉 主编《飞机总体设计》第 2 章 2.4 节，印刷页 17–25（交叉验证用）。

**设计思想**：把两本书的模型统一到同一个主管方程上，各约束模型只是它的特例。
这样每条约束的物理假设（过载 n、爬升率、加速度）都一目了然地显式出现，
而不是散落在各自的推导里。
"""

from __future__ import annotations

import numpy as np

from .units import G0

# --------------------------------------------------------------------------
# 极曲线
# --------------------------------------------------------------------------


def induced_drag_factor(aspect_ratio: float | np.ndarray, oswald_e: float | np.ndarray):
    """极曲线二次项系数 K1 = 1/(π A e)。刘虎 式(3.35)。"""
    denominator = np.pi * np.asarray(aspect_ratio, dtype=float) * np.asarray(
        oswald_e, dtype=float
    )
    if np.any(denominator <= 0.0):
        raise ValueError("诱导阻力因子：展弦比 A 与奥斯瓦尔德系数 e 必须为正")
    return 1.0 / denominator


def oswald_efficiency(
    aspect_ratio: float, leading_edge_sweep_deg: float = 0.0
) -> float:
    """奥斯瓦尔德系数 e 的初步估算。刘虎 式(3.36)/(3.37)。

    - 前缘后掠角为 0 时用直机翼式(3.36)：``e = 1.78(1 - 0.045 A^0.68) - 0.64``
    - 否则用后掠翼式(3.37)：``e = 4.61(1 - 0.045 A^0.68)(cosΛ)^0.15 - 3.1``

    这两式是统计拟合，结果仅作初步估算；若有相似机型数据，应直接给 ``oswald_e``。
    """
    if aspect_ratio <= 0.0:
        raise ValueError("奥斯瓦尔德系数估算：展弦比必须为正")

    base = 1.0 - 0.045 * aspect_ratio**0.68
    if leading_edge_sweep_deg == 0.0:
        return float(1.78 * base - 0.64)

    sweep_rad = np.radians(leading_edge_sweep_deg)
    return float(4.61 * base * np.cos(sweep_rad) ** 0.15 - 3.1)


def drag_coefficient(
    cl: np.ndarray | float, cd0: float, k1: float, k2: float = 0.0
):
    """阻力极曲线 C_D = K1·C_L² + K2·C_L + C_D0。刘虎 式(3.11)。

    K2 为一次项系数，初步分析时可取 0（刘虎 3.3.4 节）。
    """
    cl = np.asarray(cl, dtype=float)
    return k1 * cl**2 + k2 * cl + cd0


def lift_coefficient(
    wing_loading: np.ndarray | float,
    dynamic_pressure: np.ndarray | float,
    load_factor: float = 1.0,
    beta: float = 1.0,
):
    """由升力平衡得到的升力系数 C_L = n·β·(W/S)/q。刘虎 式(3.13)。

    Args:
        wing_loading: 翼载 W/S，N/m²。
        dynamic_pressure: 动压 q = ½ρV²，N/m²。
        load_factor: 过载 n。
        beta: 瞬时重量比 β = m/m0。

    Returns:
        C_L，标量或数组。
    """
    q = np.asarray(dynamic_pressure, dtype=float)
    if np.any(q <= 0.0):
        raise ValueError("升力系数：动压 q 必须为正")
    return load_factor * beta * np.asarray(wing_loading, dtype=float) / q


# --------------------------------------------------------------------------
# 主管方程
# --------------------------------------------------------------------------


def required_thrust_weight(
    wing_loading: np.ndarray | float,
    dynamic_pressure: np.ndarray | float,
    cd0: float,
    k1: float,
    k2: float = 0.0,
    load_factor: float = 1.0,
    beta: float = 1.0,
    alpha: float = 1.0,
    climb_rate: float = 0.0,
    acceleration: float = 0.0,
    speed: float | None = None,
):
    """约束分析**主管方程** —— 刘虎 式(3.15)。

    .. math::

        \\frac{F_0}{m_0 g} = \\frac{\\beta}{\\alpha}
            \\left\\{ K_1 n^2 C_L + K_2 n + \\frac{C_{D0}}{C_L}
                   + \\frac{\\dot h}{V} + \\frac{V\\!\\dot V}{g V} \\right\\},
        \\qquad C_L = \\frac{n\\beta (W/S)}{q}

    等价的物理解释：``T/W = 阻力/重量 + 爬升率/速度 + 加速度/g``。

    每条约束只是本式的一个特例：

    ==================== ====== ========= ========== =====
    约束                  n      dh/dt     dV/dt      式号
    ==================== ====== ========= ========== =====
    最大平飞速度          1      0         0          (3.24)
    爬升率                1      ROC       0          (3.23)
    水平加减速            1      0         a          (3.25)
    持续盘旋过载          n      0         0          (3.27)
    ==================== ====== ========= ========== =====

    Args:
        wing_loading: 翼载 W/S，N/m²。
        dynamic_pressure: 动压 q = ½ρV²，N/m²。
        cd0: 零升阻力系数 C_D0。
        k1: 极曲线二次项系数 K1。
        k2: 极曲线一次项系数 K2，初步分析取 0。
        load_factor: 过载 n。
        beta: 瞬时重量比 β（该状态重量 / 起飞重量）。
        alpha: 推力比 α（该状态安装推力 / 海平面静推力）。
        climb_rate: 爬升率 dh/dt，m/s。
        acceleration: 水平加速度 dV/dt，m/s²。
        speed: 飞行速度 V，m/s；``climb_rate`` 非零时必需。

    Returns:
        F0/(m0 g)，标量或与 ``wing_loading`` 同形状的数组。

    Raises:
        ValueError: 参数非法（q ≤ 0、α 或 β 非正、缺 speed 等）。
    """
    if alpha <= 0.0:
        raise ValueError("主管方程：推力比 α 必须为正")
    if beta <= 0.0:
        raise ValueError("主管方程：瞬时重量比 β 必须为正")
    if load_factor <= 0.0:
        raise ValueError("主管方程：过载 n 必须为正")

    q = np.asarray(dynamic_pressure, dtype=float)
    if np.any(q <= 0.0):
        raise ValueError("主管方程：动压 q 必须为正")

    energy_term = acceleration / G0
    if climb_rate != 0.0:
        if speed is None or speed <= 0.0:
            raise ValueError("主管方程：climb_rate 非零时必须给出为正的 speed")
        energy_term += climb_rate / float(speed)

    w = np.asarray(wing_loading, dtype=float)
    cl = load_factor * beta * w / q
    drag_term = k1 * load_factor**2 * cl + k2 * load_factor + cd0 / cl

    return (beta / alpha) * (drag_term + energy_term)


# --------------------------------------------------------------------------
# 发动机推力比 α 估算
# --------------------------------------------------------------------------


def thrust_lapse_high_bypass_turbofan(mach: float, density_ratio: float) -> float:
    """高涵道比涡扇发动机推力比 α。刘虎 式(3.38)。

    ``α = {0.568 + 0.25(1.2 - Ma)³} · σ^0.6``
    """
    return float((0.568 + 0.25 * (1.2 - mach) ** 3) * density_ratio**0.6)


def thrust_lapse_low_bypass_mil(mach: float, density_ratio: float) -> float:
    """带加力低涵道比混合涡扇 —— 军用推力状态。刘虎 式(3.39)。"""
    return float(0.72 * (0.88 + 0.245 * abs(mach - 1.6) ** 1.4) * density_ratio**0.7)


def thrust_lapse_low_bypass_max(mach: float, density_ratio: float) -> float:
    """带加力低涵道比混合涡扇 —— 最大推力状态。刘虎 式(3.40)。"""
    return float((0.94 + 0.38 * (mach - 0.4) ** 2) * density_ratio**0.7)
