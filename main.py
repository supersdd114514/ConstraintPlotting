"""飞机总体设计约束分析 —— 唯一入口。

流程：读取总设参数 → 自动发现约束模型 → 求交得到设计可行域 → 输出图表。

用法::

    python main.py
    python main.py --output output/my_design.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无窗环境也能出图；需要交互窗口时改为 "TkAgg"

from config.params import DesignParams          # noqa: E402
from constraints import discover_constraints    # noqa: E402
from core.analyzer import DEFAULT_TW_MAX, analyze  # noqa: E402
from core.validator import MissingParameterError   # noqa: E402
from plotting.plot_region import configure_fonts, plot_region  # noqa: E402


def _configure_console_encoding() -> None:
    """避免中文 Windows 控制台下因编码问题中断程序。

    中文 Windows 上 Python 默认按本地编码（cp936）写 stdout，遇到 ``²``
    这类 cp936 无法表示的字符会抛 UnicodeEncodeError 直接中断。

    **只加 ``errors="replace"``，不改编码** —— 换成 UTF-8 会让 PowerShell
    等按本地编码解码的终端显示成乱码。这样中文照常显示，个别特殊字符降级为
    ``?``，程序不会崩。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="飞机总体设计约束分析与可行域绘图")
    parser.add_argument(
        "-o", "--output",
        default="output/constraint_analysis.png",
        help="输出图片路径（默认 output/constraint_analysis.png）",
    )
    parser.add_argument(
        "--tw-max",
        type=float,
        default=1.2,
        help=f"推重比绘图窗口上限（默认 1.2，硬上限 {DEFAULT_TW_MAX}）",
    )
    return parser.parse_args()


def main() -> int:
    _configure_console_encoding()
    args = parse_args()

    params = DesignParams()

    constraints = discover_constraints()
    if not constraints:
        print("错误：constraints/ 目录下没有发现任何约束模型。", file=sys.stderr)
        return 1

    print(f"发现 {len(constraints)} 条约束：")
    for item in constraints:
        meta = item.meta
        print(
            f"  - {meta.name_cn}（{item.key}，{meta.kind.value}，{meta.sense.value}）"
            f"  ← {meta.reference}"
        )
    print()

    try:
        region = analyze(constraints, params, tw_range=(0.0, args.tw_max))
    except MissingParameterError as exc:
        print(f"参数预检失败：\n{exc}", file=sys.stderr)
        return 1

    print(region.describe())
    print()

    font = configure_fonts()
    if font is None:
        print("警告：未找到中文字体，图中的中文可能显示为方框。", file=sys.stderr)

    target = plot_region(region, args.output)
    print(f"图表已输出：{Path(target).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
