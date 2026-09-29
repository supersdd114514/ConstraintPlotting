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

    fig, ax = plt.subplots(figsize=(11.0, 7.0), constrained_layout=True)

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

    ax.legend(loc="best", fontsize=8.5, framealpha=0.93)

    # ---- 公式出处（可溯源） ----
    citations = "\n".join(
        f"· {t.meta.name_cn}：{t.meta.reference}"
        for t in sorted(region.traces, key=lambda x: x.key)
    )
    fig.text(
        0.01, 0.005,
        "公式出处：\n" + citations,
        fontsize=6.6, color="#555555", va="bottom", ha="left",
    )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=dpi)
    plt.close(fig)

    return target
