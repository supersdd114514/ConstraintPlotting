"""<约束中文名> 约束曲线模型。

公式出处：<书名> <章节/页码>
原始形式（<原单位制>）：<公式原文或编号>
本实现已换算为 SI 单位（N、m、s、kg、rad）。
"""

from __future__ import annotations

import numpy as np

from .base import ConstraintKind, ConstraintMeta, register_constraint


@register_constraint(
    ConstraintMeta(
        key="<key>",                          # 与文件名一致（snake_case）
        name_cn="<约束中文名>",                # 会出现在图例上
        category="<分类>",                     # 起飞 / 着陆 / 爬升 / 巡航 / 机动 / 限制
        sense=">=",                           # ">=" 曲线上方可行；"<=" 下方可行
        kind=ConstraintKind.CURVE,            # CURVE / VERTICAL / HORIZONTAL
        requires=(                            # 公式中用到的全部 params 字段
            "<param_a>",
            "<param_b>",
        ),
        reference="<书名> <章节/页码>",
    )
)
def compute(params, ws: np.ndarray) -> np.ndarray | float:
    """计算 <约束中文名> 对应的约束曲线。

    Args:
        params: 总设参数对象，定义于 config/params.py。
        ws: 翼载数组，单位 N/m²。

    Returns:
        CURVE / HORIZONTAL：与 ws 同形状的推重比 T/W 数组。
        VERTICAL：一个标量，表示 W/S 的限值（N/m²）。
    """
    # 1) 从 params 取出依赖参数（不要写死数值）
    #    例：cl_max = params.cl_max_takeoff

    # 2) 用 numpy 向量化实现公式，禁止 Python 循环逐点计算

    # 3) 除零保护：ws -> 0 时公式常发散，
    #    用 with np.errstate(divide="ignore", invalid="ignore") 抑制告警，
    #    再用掩码或 np.clip 把结果限制在合理区间，避免 inf/nan 污染坐标轴

    raise NotImplementedError("<约束中文名> 尚未实现")
