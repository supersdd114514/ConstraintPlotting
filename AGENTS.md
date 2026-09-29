# AGENTS.md

飞机总体设计**约束分析**工具：在「翼载 W/S — 推重比 T/W」平面上绘制各项飞行性能约束曲线，求交集得到**设计可行域**并绘图输出。

> 仓库当前为**待开发状态**：仅有 `参考文献/`（李为吉 主编《飞机总体设计》、《飞机总体设计》刘虎 等）与空的 `.gitignore`，尚无源码。
> 下文的架构与约定是**已确认的目标**，新增代码请严格遵循；若确需偏离，先说明理由再改。

## 领域约定（最重要，先读这段）

坐标系固定为 **x = 翼载 W/S，y = 推重比 T/W**。每条约束在平面上是一条曲线或一条竖直/水平边界，曲线的一侧为可行；**设计可行域 = 所有约束可行半平面的交集**。

**方向判据（用于交叉验证 `sense`）**：参考文献的选取规则是「推重比取各准则所得值的**最大值**，翼载取各准则所得值的**最小值**」。由此可得 —— **所有 T/W 类约束的 `sense` 均为 `>=`，所有 W/S 类约束的 `sense` 均为 `<=`**。拿不准方向时用这条反查。

- **量纲统一 SI**：内部计算一律 N、m、s、kg、rad。文献公式多为英制（lb/ft），抄录时必须换算，并在注释中保留原始形式以便复核。
- **W/S 内部一律用 N/m²**，展示时可换算为 kg/m²；图轴标签必须写清单位。
- **`sense` 方向必须正确**：`>=` 表示曲线（含）上方可行，`<=` 表示下方可行。方向写反会让可行域完全错误，而图表看起来仍然"正常"，极难发现 —— 这是本项目的**头号易错点**。
- **公式必须可溯源**：每个模型用 `reference` 字段标注出处（书名 + 章节/页码）。**禁止凭记忆写公式**；查不到出处就先问用户。
- 典型约束族：起飞距离、着陆距离、爬升率 / 爬升梯度、巡航速度、机动过载（稳定盘旋 / 瞬时）、失速速度、升限、加速性。
- 同类约束（如不同高度或温度下的爬升率）**取最严者**参与最终求交。

## 架构

```text
main.py               # 唯一入口：读取参数 → 运行分析 → 输出图表
config/params.py      # 用户输入的总设参数（唯一数据源，带单位注释）
constraints/          # 约束曲线模型库 —— 面向使用者的插件目录
  base.py             # 接口契约：ConstraintMeta / register_constraint / ConstraintKind
  registry.py         # 注册表 + 目录自动发现
  takeoff_distance.py # 每个约束一个文件，文件名 = key 的 snake_case
core/                 # 与具体约束无关的算法（纯计算）
  units.py            #   单位换算 + 国际标准大气 ISA
  numeric.py          #   数值保护：抑制告警、清理 inf/nan
  validator.py        #   缺参预检
  analyzer.py         #   求交、可行域提取、诊断报告
plotting/             # 只负责绘图，不参与任何计算
tools/                # 开发辅助脚本（渲染扫描书页面等），不参与运行时
output/               # 生成的图表（不入库）
参考文献/              # 只读参考书 PDF
```

## 插件契约（`constraints/` 的核心价值）

新增约束 = **往 `constraints/` 放一个文件**，不改动任何其他代码。目录由 `pkgutil.iter_modules` 自动发现。每个模型文件必须：

1. 定义签名固定的函数 `(params, ws: np.ndarray) -> np.ndarray | float`
2. 用 `@register_constraint(ConstraintMeta(...))` 装饰，声明 `key`、`name_cn`、`category`、`sense`、`kind`、`requires`、`reference`
3. 通过 `requires` 列全部依赖的参数名，供 `core/` 做**缺参预检**（宁可启动即报错，也不要跑出一张空图）
4. 全部使用 numpy 向量化运算，禁止 Python 循环逐点累加
5. 做除零与非法值保护（见「常见陷阱」）

`kind` 三种取值：

| `kind` | 含义 | 典型约束 |
| --- | --- | --- |
| `curve` | y = f(x)，T/W 随 W/S 变化 | 起飞距离、爬升率、巡航速度、机动过载 |
| `vertical` | x = const，纯翼载限值 | 着陆距离、失速速度 |
| `horizontal` | y = const，纯推重比下限 | 海平面静推力要求 |

**自动发现遇到 import 失败必须直接抛出，不得静默跳过。**

完整操作流程见 skill：[`.github/skills/add-constraint-model/SKILL.md`](./.github/skills/add-constraint-model/SKILL.md)（也可输入 `/add-constraint-model`）。

## 代码风格

- **标识符用英文，注释与 docstring 用中文**。
- 物理量命名带明确含义：`wing_loading`、`thrust_weight_ratio`、`climb_rate`、`cl_max_takeoff`。
- **单位换算集中在 `core/units.py`**，禁止在各模型里散落 `* 0.3048` 之类的魔数。
- 区分职责：`core/` 与 `constraints/` 是纯计算，不做 I/O、不画图、不读配置文件。
- 数值计算函数加类型标注。

## 运行与验证

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py                                      # 输出 output/constraint_analysis.png
python main.py --tw-max 0.8 -o output/low_tw.png    # 收窄推重比绘图窗口
```

运行时会在终端打印当前**全部已注册约束及其公式出处**，这是核对「插件是否真的生效」最快的方式。

改动约束模型后**必须实际跑一次并查看产出的图**，不能只靠读代码判断正确性。

## 常见陷阱

- **可行域为空**：通常是某条 `sense` 写反，或某条约束过严，而不是"参数没调好"。先查方向，再查数值。
- **混淆 W/S 的 N/m² 与 kg/m²**：两者相差约 9.8 倍，混用会让可行域整体偏移。
- **曲线出现 `inf` / `nan`**：`ws` 接近 0 或速度项为 0 时公式发散。用 `np.errstate` + 掩码或截断处理，否则 matplotlib 的自动坐标范围会被拉飞，图完全不可读。
- **模型里写死高度、温度、速度**：这些应来自 `params`，否则无法做多工况批量对比。
- **忘记加 `@register_constraint` 装饰器**：约束静默不生效，图上看不出任何异常 —— 最典型的"插件没生效"原因。
- **用绘图窗口上界做数值截断**：清理 `inf`/`nan` 必须用**与窗口无关的硬上限**（`core.analyzer.HARD_TW_CAP` / `HARD_WS_CAP`）。若拿窗口上界截断，超出窗口的约束会被裁剪到窗口范围内，**约束被悄悄削弱、可行域虚假变大** —— 把窗口调窄就能"造出"一块可行域。本项目已实际踩过此坑，改截断逻辑后必须回归验证「窗口 (0, 0.2) → 可行域为空」。
- **在模型文件里做单位换算**：换算逻辑应集中在 `core/units.py`，散落会难以审计。
- **模型返回 `nan` 时当作可行**：`nan` 表示公式**无定义**，必须判为不可行；只有 `inf` 才可截断到硬上限。两者语义不同，不可混为一谈。
- **中文 Windows 控制台编码**：`N/m²` 的 `²` 在 cp936 下无法编码，会让 `print` 抛 `UnicodeEncodeError` 中断程序。`main.py` 已用 `reconfigure(errors="replace")` 兜底；**不要改成 `encoding="utf-8"`**，那会让 PowerShell 管道输出变成乱码。

## 参考

- `参考文献/` 下两本《飞机总体设计》是公式的唯一权威来源，只读，不要修改或移动。
  - 两本 PDF 均为**纯扫描图像、无文本层**，`pypdf` 提取不到任何文字。需要用 `pymupdf` 把页面渲染成 PNG 后再读图，见下方「查阅扫描书的方法」。
  - 已确认：李为吉《飞机总体设计》第 2 章 **2.4 节「确定推重比和翼载」**（印刷页 17–25）是约束分析的核心章节。
- **李为吉书中 W/S 的单位是 9.8 N/m²（即 kgf/m²）**，见其表 2.9 表头；公式系数是按该单位标定的，代入 N/m² 前必须换算。已实现的模型在 docstring 中保留了原式。
- 需要新增约束或修正数学模型时，走 `/add-constraint-model` 流程。

### 查阅扫描书的方法

```powershell
pip install pymupdf                       # 仅本工具需要，不是项目运行依赖
python tools\render_reference_pages.py 0 29 39 --dpi 160
```

`book 0` = 李为吉（**印刷页 = PDF 页 − 13**），`book 1` = 刘虎。
渲染结果落在 `output/reference_pages/book<N>/`，随后直接读图。
