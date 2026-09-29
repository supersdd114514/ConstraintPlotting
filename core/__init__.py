"""与具体约束无关的算法层：单位换算、数值保护、缺参预检、求交、可行域提取。

本层是**纯计算**：不做 I/O、不画图、不读配置文件。
"""

from .analyzer import (
    DEFAULT_TW_MAX,
    ConstraintTrace,
    FeasibleRegion,
    analyze,
)
from .validator import MissingParameterError, check_all

__all__ = [
    "DEFAULT_TW_MAX",
    "ConstraintTrace",
    "FeasibleRegion",
    "MissingParameterError",
    "analyze",
    "check_all",
]
