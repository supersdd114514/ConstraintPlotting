"""单位换算与标准大气（ISA）。

所有单位换算集中在此，模型文件中**禁止**出现 `* 0.3048` 之类的换算魔数。
内部计算一律 SI：N、m、s、kg、rad、K。

注意：参考文献（李为吉《飞机总体设计》等）中的 W/S 常以 **9.8 N/m²（kgf/m²）**
为单位，抄录公式时必须显式换算，见 `wing_loading_kgf_to_n`。
"""

from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------
# 基本物理常数
# --------------------------------------------------------------------------
G0 = 9.80665            # 标准重力加速度, m/s²
RHO0 = 1.225            # 海平面标准大气密度, kg/m³
P0 = 101325.0           # 海平面标准大气压, Pa
T0 = 288.15             # 海平面标准温度, K
LAPSE = 0.0065          # 对流层温度梯度, K/m
R_AIR = 287.05287       # 干空气气体常数, J/(kg·K)
GAMMA_AIR = 1.4         # 空气比热比
H_TROPOPAUSE = 11000.0  # 对流层顶, m
T_TROPOPAUSE = 216.65   # 对流层顶温度, K
H_STRATOPAUSE = 20000.0 # 平流层顶, m

# --------------------------------------------------------------------------
# 长度
# --------------------------------------------------------------------------
FT_TO_M = 0.3048
M_TO_FT = 1.0 / FT_TO_M
IN_TO_M = 0.0254
NM_TO_M = 1852.0

# --------------------------------------------------------------------------
# 质量与力
# --------------------------------------------------------------------------
LB_TO_KG = 0.45359237
KG_TO_LB = 1.0 / LB_TO_KG
LBF_TO_N = 4.4482216152605
N_TO_LBF = 1.0 / LBF_TO_N
HP_TO_W = 745.6998715822702  # 英制马力, W

# --------------------------------------------------------------------------
# 速度
# --------------------------------------------------------------------------
KT_TO_MPS = NM_TO_M / 3600.0     # 1 kn = 1 n mile/h
MPS_TO_KT = 1.0 / KT_TO_MPS
KMH_TO_MPS = 1.0 / 3.6
MPS_TO_KMH = 3.6
MPH_TO_MPS = 1609.344 / 3600.0
FPM_TO_MPS = FT_TO_M / 60.0      # ft/min
MPS_TO_FPM = 1.0 / FPM_TO_MPS

# --------------------------------------------------------------------------
# 角度
# --------------------------------------------------------------------------
DEG_TO_RAD = np.pi / 180.0
RAD_TO_DEG = 180.0 / np.pi


def celsius_to_kelvin(t_celsius: float | np.ndarray) -> float | np.ndarray:
    """摄氏度 → 开尔文。"""
    return np.asarray(t_celsius, dtype=float) + 273.15


def kelvin_to_celsius(t_kelvin: float | np.ndarray) -> float | np.ndarray:
    """开尔文 → 摄氏度。"""
    return np.asarray(t_kelvin, dtype=float) - 273.15


def wing_loading_kgf_to_n(ws_kgf_m2: float | np.ndarray) -> float | np.ndarray:
    """翼载 9.8 N/m²(kgf/m²) → N/m²。

    参考文献（如李为吉《飞机总体设计》表 2.9）以 9.8 N/m² 作为翼载单位，
    公式中的数值系数是按该单位标定的，必须在换算后再代入。
    """
    return np.asarray(ws_kgf_m2, dtype=float) * G0


def wing_loading_n_to_kgf(ws_n_m2: float | np.ndarray) -> float | np.ndarray:
    """翼载 N/m² → 9.8 N/m²(kgf/m²)。"""
    return np.asarray(ws_n_m2, dtype=float) / G0


def wing_loading_n_to_kg(ws_n_m2: float | np.ndarray) -> float | np.ndarray:
    """翼载 N/m² → kg/m²（仅供展示，不用于公式计算）。"""
    return np.asarray(ws_n_m2, dtype=float) / G0


# --------------------------------------------------------------------------
# 国际标准大气 (ISA)
# --------------------------------------------------------------------------
def isa_temperature(altitude_m: float | np.ndarray) -> float | np.ndarray:
    """ISA 温度，K。适用 0~20 km。"""
    h = np.asarray(altitude_m, dtype=float)
    troposphere = T0 - LAPSE * h
    return np.where(h <= H_TROPOPAUSE, troposphere, T_TROPOPAUSE)


def isa_pressure(altitude_m: float | np.ndarray) -> float | np.ndarray:
    """ISA 压力，Pa。适用 0~20 km。"""
    h = np.asarray(altitude_m, dtype=float)

    # 对流层：p = p0 (T/T0)^(g0/(L R))
    exponent = G0 / (LAPSE * R_AIR)
    p_trop = P0 * np.power(T0 - LAPSE * h, exponent) / np.power(T0, exponent)

    # 平流层（等温）：p = p11 exp(-g0 (h - h11)/(R T11))
    p_tropopause = P0 * np.power(
        T_TROPOPAUSE / T0, exponent
    )  # 即 h = 11 km 处的压力
    p_strat = p_tropopause * np.exp(
        -G0 * (h - H_TROPOPAUSE) / (R_AIR * T_TROPOPAUSE)
    )

    return np.where(h <= H_TROPOPAUSE, p_trop, p_strat)


def isa_density(altitude_m: float | np.ndarray) -> float | np.ndarray:
    """ISA 密度，kg/m³。适用 0~20 km。"""
    return isa_pressure(altitude_m) / (R_AIR * isa_temperature(altitude_m))


def isa_density_ratio(altitude_m: float | np.ndarray) -> float | np.ndarray:
    """密度比 σ = ρ_H / ρ_0（无量纲）。"""
    return isa_density(altitude_m) / RHO0


def isa_speed_of_sound(altitude_m: float | np.ndarray) -> float | np.ndarray:
    """ISA 声速，m/s。a = sqrt(γ R T)。"""
    return np.sqrt(GAMMA_AIR * R_AIR * isa_temperature(altitude_m))


def dynamic_pressure(
    density: float | np.ndarray, speed: float | np.ndarray
) -> float | np.ndarray:
    """动压 q = ½ρV²，N/m²。"""
    density = np.asarray(density, dtype=float)
    speed = np.asarray(speed, dtype=float)
    return 0.5 * density * speed**2
