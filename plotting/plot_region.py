"""可行域绘图。

本模块**只负责画图**，不参与任何计算：所有数值都来自 `core.analyzer` 的产物。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from constraints.base import ConstraintKind, Sense
from core.analyzer import FeasibleRegion
from core.units import G0, wing_loading_n_to_kg

# 可行的填充色与各约束的线色
_REGION_COLOR = "#4CAF50"
_CURVE_COLOR = "#D32F2F"
_VERTICAL_COLOR = "#1976D2"
_HORIZONTAL_COLOR = "#7B1FA2"
_POINT_COLOR = "#FF6F00"
_DESIGN_COLOR = "#0D47A1"       # 当前设计点落在可行域内
_VIOLATION_COLOR = "#C62828"    # 当前设计点不满足部分约束

_CJK_FONTS = (
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "PingFang SC",
)


def configure_fonts() -> str | None:
    """挑选一个可用的中文字体，避免图例与轴标签显示成方框。

    Returns:
        实际选用的字体名；未找到时返回 None（图上中文会变成方框，需要装字体）。
    """
    from matplotlib import font_manager

    available = {font.name for font in font_manager.fontManager.ttflist}
    for name in _CJK_FONTS:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False  # 负号正常显示
            return name
    return None


def _label_of(trace) -> str:
    """生成图例文本。"""
    meta = trace.meta
    if trace.kind is ConstraintKind.CURVE:
        arrow = "T/W ≥" if trace.sense is Sense.GE else "T/W ≤"
        return f"{meta.name_cn}（{arrow} 曲线）"
    if trace.kind is ConstraintKind.VERTICAL:
        arrow = "W/S ≤" if trace.sense is Sense.LE else "W/S ≥"
        return f"{meta.name_cn}（{arrow} {trace.ws_bound:.0f} N/m²）"
    arrow = "T/W ≥" if trace.sense is Sense.GE else "T/W ≤"
    return f"{meta.name_cn}（{arrow} {trace.tw_bound:.3f}）"


def plot_region(
    region: FeasibleRegion,
    output_path: str | Path = "output/constraint_analysis.png",
    title: str = "飞机总体设计约束分析与设计可行域",
    dpi: int = 160,
) -> Path:
    """把可行域与各约束曲线画成一张图并保存。

    Args:
        region: `core.analyzer.analyze` 的返回值。
        output_path: 输出图片路径。
        title: 图标题。
        dpi: 输出分辨率。

    Returns:
        实际写出的文件路径。
    """
    configure_fonts()

    ws_grid = region.ws_grid
    tw_grid = region.tw_grid
    ws2d, tw2d = np.meshgrid(ws_grid, tw_grid)

    # 引文区布局：约束变多后单列会溢出，改为多列并预留底部空间
    traces_sorted = sorted(region.traces, key=lambda t: t.key)
    n_cite = len(traces_sorted)
    n_cols = 2 if n_cite > 6 else 1
    cite_rows = -(-n_cite // n_cols)
    line_step = 0.0175
    bottom = 0.085 + line_step * cite_rows

    fig, ax = plt.subplots(figsize=(11.5, 7.6))

    # ---- 可行域填充 ----
    if not region.is_empty:
        ax.contourf(
            ws2d, tw2d, region.mask.astype(float),
            levels=[0.5, 1.5],
            colors=[_REGION_COLOR],
            alpha=0.22,
            zorder=1,
        )
        # 边界描边，让可行域轮廓更清晰
        ax.contour(
            ws2d, tw2d, region.mask.astype(float),
            levels=[0.5],
            colors=[_REGION_COLOR],
            linewidths=2.0,
            zorder=2,
        )

    # ---- 各约束曲线 / 边界 ----
    for trace in region.traces:
        label = _label_of(trace)
        if trace.kind is ConstraintKind.CURVE:
            finite = np.isfinite(trace.curve) & (trace.curve <= tw_grid[-1])
            ax.plot(
                trace.ws[finite], trace.curve[finite],
                color=_CURVE_COLOR, linewidth=1.9, label=label, zorder=4,
            )
        elif trace.kind is ConstraintKind.VERTICAL:
            ax.axvline(
                trace.ws_bound, color=_VERTICAL_COLOR,
                linewidth=1.9, linestyle="--", label=label, zorder=4,
            )
        else:
            ax.axhline(
                trace.tw_bound, color=_HORIZONTAL_COLOR,
                linewidth=1.9, linestyle="-.", label=label, zorder=4,
            )

    # ---- 推荐设计点 ----
    point = region.min_thrust_point
    if point is not None:
        ws_p, tw_p = point
        ax.plot(
            ws_p, tw_p, marker="*", markersize=18, color=_POINT_COLOR,
            markeredgecolor="white", markeredgewidth=1.2, zorder=6,
            label=f"推荐设计点 W/S={ws_p:.0f}, T/W={tw_p:.3f}",
        )

    # ---- 当前设计点（由 takeoff_weight / wing_area / takeoff_thrust 定位）----
    current = region.current_design_point
    if current is not None:
        ws_c, tw_c = current
        feasible = region.evaluate_point(ws_c, tw_c).feasible
        inside = (
            ws_grid[0] <= ws_c <= ws_grid[-1] and tw_grid[0] <= tw_c <= tw_grid[-1]
        )
        if inside:
            ax.plot(
                ws_c, tw_c, marker="o", markersize=11,
                color=_DESIGN_COLOR if feasible else _VIOLATION_COLOR,
                markeredgecolor="white", markeredgewidth=1.4, zorder=7,
                label=("当前设计点" if feasible else "当前设计点（不满足约束）")
                + f" W/S={ws_c:.0f}, T/W={tw_c:.3f}",
            )
        else:
            ax.text(
                0.985, 0.028,
                f"当前设计点 W/S={ws_c:.0f}, T/W={tw_c:.3f}\n超出绘图窗口范围",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5,
                color=_VIOLATION_COLOR,
                bbox=dict(boxstyle="round", fc="white", ec=_VIOLATION_COLOR, alpha=0.92),
            )

    # ---- 坐标轴 ----
    ax.set_xlim(ws_grid[0], ws_grid[-1])
    ax.set_ylim(tw_grid[0], tw_grid[-1])
    ax.set_xlabel("翼载 W/S  (N/m²)")
    ax.set_ylabel("推重比 T/W")

    # 顶部附加 kg/m² 刻度 —— 主动提醒两个单位差 9.8 倍
    secax = ax.secondary_xaxis("top", functions=(wing_loading_n_to_kg, lambda v: v * G0))
    secax.set_xlabel("翼载 W/S  (kg/m²)")

    ax.set_title(title, fontsize=14, pad=38, fontweight="bold")
    ax.grid(alpha=0.3, linestyle=":", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    if region.is_empty:
        ax.text(
            0.5, 0.5, "设计可行域为空",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=20, color=_CURVE_COLOR, fontweight="bold", alpha=0.85,
        )

    ax.legend(loc="best", fontsize=8.2, framealpha=0.93)

    # ---- 公式出处（可溯源）----
    # 只展示第一出处，完整引用（含交叉验证来源）见模型文件的 docstring
    fig.subplots_adjust(left=0.075, right=0.985, top=0.845, bottom=bottom)
    fig.text(
        0.075, bottom - 0.020, "公式出处：",
        fontsize=7.2, color="#333333", va="top", ha="left", fontweight="bold",
    )
    for idx, trace in enumerate(traces_sorted):
        col, row = divmod(idx, cite_rows)
        primary = trace.meta.reference.split("；")[0]
        fig.text(
            0.075 + col * 0.465,
            bottom - 0.042 - row * line_step,
            f"· {trace.meta.name_cn}：{primary}",
            fontsize=6.3, color="#555555", va="top", ha="left",
        )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=dpi)
    plt.close(fig)

    return target
