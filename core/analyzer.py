"""约束求交与可行域提取。

本模块与具体约束**无关**：只消费注册表中的模型函数，在 (W/S, T/W) 网格上判定
每个网格点是否满足全部约束，其交集即**设计可行域**。

量纲约定：``ws`` 为 N/m²，``tw`` 为无量纲。

设计要点：

- 同类约束（如不同高度或温度下的爬升率）**取最严者**参与求交 —— 这一点由
  「全部约束逻辑与」自动实现，无需额外处理。
- 模型返回 ``nan`` 的点（公式无定义）按**不可行**处理，不允许用错误数据
  "造出"一块可行域。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from constraints.base import ConstraintKind, RegisteredConstraint, Sense

from .numeric import sanitize_bound, sanitize_curve
from .validator import check_all

DEFAULT_TW_MIN = 0.0
DEFAULT_TW_MAX = 3.0      # 推重比绘图/截断上限
DEFAULT_WS_RANGE = (500.0, 6000.0)   # N/m²，无法推断时的兜底
_DUMMY_WS = np.array([1000.0, 2000.0, 3000.0])

# 数值清理用的**硬上限**，必须与绘图窗口无关。
# 若拿绘图窗口上界去清理，超窗口的约束会被裁剪到窗口上界而**被悄悄削弱**，
# 可行域会虚假地变大 —— 调窄窗口就"造出"可行域，属于致命错误。
HARD_TW_CAP = 10.0        # 无量纲
HARD_WS_CAP = 1.0e6       # N/m²


@dataclass
class ConstraintTrace:
    """单条约束在一次分析中的计算痕迹，供绘图、诊断与报告使用。"""

    registered: RegisteredConstraint
    kind: ConstraintKind
    sense: Sense
    ws: np.ndarray                       # 求值所用的 W/S 网格
    curve: np.ndarray | None = None      # CURVE：逐点所需 T/W
    ws_bound: float | None = None        # VERTICAL：W/S 限值
    tw_bound: float | None = None        # HORIZONTAL：T/W 限值
    nan_count: int = 0                   # 公式无定义的点数
    feasible_fraction: float = 0.0       # 仅该约束时可行面积占比，用于定位谁在"卡"

    @property
    def key(self) -> str:
        return self.registered.key

    @property
    def meta(self):
        return self.registered.meta


@dataclass
class PointEvaluation:
    """对平面上某一点的设计校核结果。"""

    ws: float
    tw: float
    feasible: bool
    violated: list[str]          # 未满足的约束 key


@dataclass
class FeasibleRegion:
    """设计可行域。"""

    ws_grid: np.ndarray
    tw_grid: np.ndarray
    mask: np.ndarray
    traces: list[ConstraintTrace]
    params: Any = None

    @property
    def is_empty(self) -> bool:
        return not bool(self.mask.any())

    @property
    def area_fraction(self) -> float:
        """可行域占整个绘图窗口的面积比。"""
        return float(self.mask.mean())

    @property
    def ws_bounds(self) -> tuple[float, float] | None:
        cols = self.mask.any(axis=0)
        if not cols.any():
            return None
        return float(self.ws_grid[cols].min()), float(self.ws_grid[cols].max())

    @property
    def tw_bounds(self) -> tuple[float, float] | None:
        rows = self.mask.any(axis=1)
        if not rows.any():
            return None
        return float(self.tw_grid[rows].min()), float(self.tw_grid[rows].max())

    @property
    def min_thrust_point(self) -> tuple[float, float] | None:
        """可行域内 T/W 最小的设计点 —— 最省推力（通常也最省油）的方案。

        同一 T/W 上取 W/S 较大者，机翼更小、结构更轻。
        """
        if self.is_empty:
            return None
        row = int(np.flatnonzero(self.mask.any(axis=1)).min())
        col = int(np.flatnonzero(self.mask[row]).max())
        return float(self.ws_grid[col]), float(self.tw_grid[row])

    @property
    def current_design_point(self) -> tuple[float, float] | None:
        """用户当前设计在 (W/S, T/W) 平面上的位置。

        由 ``takeoff_weight``、``wing_area``、``takeoff_thrust`` 三个参数确定。
        缺任一参数则返回 None。

        注意：可行域本身与总重**无关**，改动总重只会移动本点，
        不会改变可行域 —— 这是约束分析的固有性质，不是缺陷。
        """
        if self.params is None:
            return None

        weight = getattr(self.params, "takeoff_weight", None)
        area = getattr(self.params, "wing_area", None)
        thrust = getattr(self.params, "takeoff_thrust", None)
        if not weight or not area or not thrust:
            return None
        if weight <= 0.0 or area <= 0.0:
            return None

        return float(weight / area), float(thrust / weight)

    def evaluate_point(self, ws: float, tw: float) -> PointEvaluation:
        """校核平面上任意一点，列出它未满足的约束。

        Args:
            ws: 翼载, N/m²。
            tw: 推重比。

        Returns:
            `PointEvaluation`。
        """
        violated: list[str] = []

        for trace in self.traces:
            if trace.kind is ConstraintKind.CURVE:
                required = float(np.interp(ws, trace.ws, trace.curve))
                if not np.isfinite(required):
                    violated.append(trace.key)
                    continue
                ok = (
                    tw >= required
                    if trace.sense is Sense.GE
                    else tw <= required
                )
            elif trace.kind is ConstraintKind.VERTICAL:
                ok = (
                    ws <= trace.ws_bound
                    if trace.sense is Sense.LE
                    else ws >= trace.ws_bound
                )
            else:
                ok = (
                    tw >= trace.tw_bound
                    if trace.sense is Sense.GE
                    else tw <= trace.tw_bound
                )

            if not ok:
                violated.append(trace.key)

        return PointEvaluation(ws=ws, tw=tw, feasible=not violated, violated=violated)

    def sizing_at(self, ws: float, tw: float) -> tuple[float, float] | None:
        """把可行域上的一点折算成具体的机翼面积与推力。

        Returns:
            ``(机翼面积 S / m², 海平面静推力 F0 / N)``；缺总重参数时返回 None。
        """
        if self.params is None:
            return None
        weight = getattr(self.params, "takeoff_weight", None)
        if not weight or weight <= 0.0 or ws <= 0.0:
            return None
        return float(weight / ws), float(weight * tw)

    def describe(self) -> str:
        """生成人类可读的结论摘要。"""
        from .units import wing_loading_n_to_kg

        lines: list[str] = []
        if self.is_empty:
            lines.append("设计可行域为空！所有约束无公共交集。")
            lines.append("")
            lines.append("排查顺序（见 AGENTS.md 常见陷阱）：")
            lines.append("  1. 逐条核对各约束的 sense 方向是否写反；")
            lines.append("  2. 检查参数单位是否混用了 N/m² 与 kg/m²；")
            lines.append("  3. 检查是否有单条约束过严（下方 feasible_fraction 最小者）。")
            lines.append("")
            lines.append("各约束单独作用时的可行面积占比（越小越受它限制）：")
            for t in sorted(self.traces, key=lambda x: x.feasible_fraction):
                lines.append(
                    f"  {t.feasible_fraction:6.1%}  {t.key}（{t.meta.name_cn}）"
                )
            return "\n".join(lines)

        lines.append("设计可行域非空。")
        lines.append(
            f"  可行面积占比：{self.area_fraction:.1%}"
            f"（窗口 W/S {self.ws_grid[0]:.0f}~{self.ws_grid[-1]:.0f} N/m²，"
            f"T/W {self.tw_grid[0]:.2f}~{self.tw_grid[-1]:.2f}）"
        )
        if self.ws_bounds:
            lo, hi = self.ws_bounds
            lines.append(
                f"  翼载 W/S 可行区间：{lo:.0f} ~ {hi:.0f} N/m²"
                f"（{wing_loading_n_to_kg(lo):.1f} ~ {wing_loading_n_to_kg(hi):.1f} kg/m²）"
            )
        if self.tw_bounds:
            lo, hi = self.tw_bounds
            lines.append(f"  推重比 T/W 可行区间：{lo:.3f} ~ {hi:.3f}")

        point = self.min_thrust_point
        if point is not None:
            ws, tw = point
            lines.append(
                f"  推荐设计点（T/W 最小）：W/S = {ws:.0f} N/m²"
                f"（{wing_loading_n_to_kg(ws):.1f} kg/m²），T/W = {tw:.3f}"
            )
            sizing = self.sizing_at(ws, tw)
            if sizing is not None:
                area, thrust = sizing
                lines.append(
                    f"      折算到起飞重量 → 机翼面积 S = {area:.1f} m²，"
                    f"需海平面静推力 F0 = {thrust:,.0f} N"
                )

        current = self.current_design_point
        if current is not None:
            ws_c, tw_c = current
            evaluation = self.evaluate_point(ws_c, tw_c)
            weight = float(getattr(self.params, "takeoff_weight", 0.0))
            area = float(getattr(self.params, "wing_area", 0.0))
            lines.append("")
            lines.append(
                f"  当前设计点：W/S = {ws_c:.0f} N/m²"
                f"（{wing_loading_n_to_kg(ws_c):.0f} kg/m²，"
                f"= 起飞重量 {weight:,.0f} N ÷ 机翼面积 {area:.1f} m²）"
                f"，T/W = {tw_c:.3f}  —— "
                + ("在可行域内" if evaluation.feasible else "不在可行域内")
            )
            if evaluation.violated:
                names = [
                    t.meta.name_cn for t in self.traces if t.key in evaluation.violated
                ]
                lines.append(
                    f"      未满足的约束（{len(names)} 条）：{'、'.join(names)}"
                )
            else:
                lines.append("      全部约束均满足")

        lines.append("")
        lines.append(
            "  注：可行域只取决于 W/S 与 T/W，与总重**无关**。改动起飞重量 /"
        )
        lines.append(
            "      机翼面积只会移动「当前设计点」，不会改变可行域本身。"
        )

        lines.append("")
        lines.append("参与求交的约束（按单独可行面积占比升序，越靠前越是瓶颈）：")
        for t in sorted(self.traces, key=lambda x: x.feasible_fraction):
            flag = ""
            if t.nan_count:
                flag = f"  [含 {t.nan_count} 个无定义点]"
            # 翼载限值同时给出两种单位，避免读者自行换算时误用 10 倍因子
            detail = ""
            if t.kind is ConstraintKind.VERTICAL and t.ws_bound is not None:
                relation = "≤" if t.sense is Sense.LE else "≥"
                detail = (
                    f"  W/S {relation} {t.ws_bound:.0f} N/m²"
                    f"（{wing_loading_n_to_kg(t.ws_bound):.0f} kg/m²）"
                )
            elif t.kind is ConstraintKind.HORIZONTAL and t.tw_bound is not None:
                relation = "≥" if t.sense is Sense.GE else "≤"
                detail = f"  T/W {relation} {t.tw_bound:.3f}"
            lines.append(
                f"  {t.feasible_fraction:6.1%}  {t.meta.name_cn}"
                f"（{t.key}, {t.kind.value}, {t.sense.value}）{flag}{detail}"
            )
            lines.append(f"          出处：{t.meta.reference}")
        return "\n".join(lines)


def _evaluate(
    registered: RegisteredConstraint,
    params: Any,
    ws: np.ndarray,
) -> ConstraintTrace:
    """按 kind 调用模型函数并做数值清理。

    清理一律使用 `HARD_TW_CAP` / `HARD_WS_CAP` 这些**硬上限**，与绘图窗口无关，
    从而保证"调窄窗口"不会削弱任何约束。
    """
    meta = registered.meta
    result = registered(params, ws)

    if meta.kind is ConstraintKind.CURVE:
        curve = np.asarray(result, dtype=float)
        if curve.shape != ws.shape:
            raise ValueError(
                f"约束 {meta.key!r} 返回形状 {curve.shape}，与输入 ws 形状 "
                f"{ws.shape} 不一致 —— CURVE 类型必须向量化返回同形状数组"
            )
        nan_count = int(np.isnan(curve).sum())
        return ConstraintTrace(
            registered, meta.kind, meta.sense, ws,
            curve=sanitize_curve(curve, HARD_TW_CAP), nan_count=nan_count,
        )

    value = float(result)
    if meta.kind is ConstraintKind.VERTICAL:
        return ConstraintTrace(
            registered, meta.kind, meta.sense, ws,
            ws_bound=sanitize_bound(value, HARD_WS_CAP),
        )

    return ConstraintTrace(
        registered, meta.kind, meta.sense, ws,
        tw_bound=sanitize_bound(value, HARD_TW_CAP),
    )


def _mask_of(trace: ConstraintTrace, ws2d: np.ndarray, tw2d: np.ndarray) -> np.ndarray:
    """把一条约束转成二维布尔可行掩码。"""
    if trace.kind is ConstraintKind.CURVE:
        required = trace.curve[None, :]
        if trace.sense is Sense.GE:
            mask = tw2d >= required
        else:
            mask = tw2d <= required
        # 公式无定义处不可判为可行
        return mask & np.isfinite(required)

    if trace.kind is ConstraintKind.VERTICAL:
        bound = trace.ws_bound
        return ws2d <= bound if trace.sense is Sense.LE else ws2d >= bound

    bound = trace.tw_bound
    return tw2d >= bound if trace.sense is Sense.GE else tw2d <= bound


def _suggest_ws_range(
    constraints: Sequence[RegisteredConstraint], params: Any
) -> tuple[float, float]:
    """用 VERTICAL 约束推断翼载绘图区间。

    参考文献的选取规则是「翼载取各准则所得值的最小值」，因此最**紧**的那个上限
    决定了可行域右界，窗口就以它为基准展开，而不是取所有上限中的最大值
    （否则会把图拉得很宽、可行域挤成一条线）。
    """
    uppers: list[float] = []
    lowers: list[float] = []

    for registered in constraints:
        meta = registered.meta
        if meta.kind is not ConstraintKind.VERTICAL:
            continue
        value = float(
            np.asarray(registered(params, _DUMMY_WS), dtype=float).reshape(-1)[0]
        )
        if not np.isfinite(value) or value <= 0:
            continue
        (uppers if meta.sense is Sense.LE else lowers).append(value)

    if uppers:
        cap = min(uppers)
        lo = max(cap * 0.08, 1.0)
        hi = cap * 1.8
        if lowers:
            lo = min(lo, min(lowers) * 0.8)
        return (float(lo), float(hi))

    if lowers:
        base = max(lowers)
        return (float(max(base * 0.5, 1.0)), float(base * 3.0))

    return DEFAULT_WS_RANGE


def analyze(
    constraints: Sequence[RegisteredConstraint],
    params: Any,
    ws_range: tuple[float, float] | None = None,
    tw_range: tuple[float, float] | None = None,
    n_ws: int = 600,
    n_tw: int = 600,
) -> FeasibleRegion:
    """在 (W/S, T/W) 网格上求全部约束的交集，得到设计可行域。

    Args:
        constraints: 参与求交的约束列表。
        params: 总设参数对象。
        ws_range: 翼载区间，单位 N/m²。None 时按 VERTICAL 约束自动推断。
        tw_range: 推重比区间。None 时取 ``(0, DEFAULT_TW_MAX)``。
        n_ws: W/S 方向网格数。
        n_tw: T/W 方向网格数。

    Returns:
        `FeasibleRegion`。

    Raises:
        MissingParameterError: 有约束依赖的参数缺失（在计算前拦下）。
    """
    if not constraints:
        raise ValueError("约束列表为空 —— 请确认 constraints/ 目录下有模型文件")

    check_all(constraints, params)

    tw_min, tw_max = tw_range if tw_range is not None else (DEFAULT_TW_MIN, DEFAULT_TW_MAX)
    if ws_range is None:
        ws_range = _suggest_ws_range(constraints, params)
    ws_min, ws_max = ws_range

    ws = np.linspace(ws_min, ws_max, n_ws)
    tw = np.linspace(tw_min, tw_max, n_tw)
    ws2d, tw2d = np.meshgrid(ws, tw)

    mask = np.ones_like(ws2d, dtype=bool)
    traces: list[ConstraintTrace] = []
    for registered in constraints:
        trace = _evaluate(registered, params, ws)
        own = _mask_of(trace, ws2d, tw2d)
        trace.feasible_fraction = float(own.mean())
        traces.append(trace)
        mask &= own

    return FeasibleRegion(
        ws_grid=ws, tw_grid=tw, mask=mask, traces=traces, params=params
    )
