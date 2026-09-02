<div align="center">
  <h1>mathmodel-ai</h1>
  <a href="./README.md"><b>English</b></a> | <b>中文</b>
</div>
<br>

# CUMCM 数学建模论文工厂

本项目提供一条可复现的数模竞赛论文生产与审计工作流，包含可复用的 `mathmodel-skill`、确定性 CLI 检查、证据注册表、求解/分析运行器、LaTeX 页数均衡门控、端到端测试夹具、竞赛上限基准测试以及发布打包规则。

## 当前开发阶段

Competition OS 核心与确定性基准基础设施已基本完成。当前前沿是真实案例的实证训练；继续开发前请先阅读 [docs/handoff/NEXT.md](docs/handoff/NEXT.md)。

核心 CLI 依赖见 `requirements.txt`。GitHub Actions 会在每次针对 `main` 的 push 和 pull request 上运行回归测试套件与隔离的夹具基准测试。

支持的问题类型为 `forecasting`（预测）、`optimization`（优化）、`evaluation`（评价）、`mechanism`（机理）、`simulation`（仿真）、`classification`（分类）、`statistics`（统计）和 `hybrid`（综合）。分类与统计类型包含专门的校验要求和写作参考；不支持的类型会在配置加载阶段直接报错。

## 快速开始

```text
python -m pip install -r requirements.txt
python mathmodel-skill/scripts/mathmodel.py init <project> --id <id> --title <title> --type optimization
python mathmodel-skill/scripts/mathmodel.py init <project> --id <id> --title <title> --type optimization --json
python mathmodel-skill/scripts/mathmodel.py inspect <project> --json
python mathmodel-skill/scripts/mathmodel.py build <project> --json
python mathmodel-skill/scripts/mathmodel.py audit <project> --json
python mathmodel-skill/scripts/mathmodel.py capability <project> --json
# 解析一个有界、只读的外部提供方
python mathmodel-skill/scripts/mathmodel.py capability <project> --capability red_team --provider ars --json
python mathmodel-skill/scripts/mathmodel.py package <project> --json
python mathmodel-skill/scripts/mathmodel.py run <project> --json
# 单次运行的正式 profile/mode 覆盖（不重写 mathmodel.json）
python mathmodel-skill/scripts/mathmodel.py run <project> --profile cumcm --mode competition-max --json
# 初始化正式项目（创建检查清单，绝不伪造签核）
python mathmodel-skill/scripts/mathmodel.py init <project> --id ID --title TITLE --type hybrid --profile cumcm --mode competition-assisted
```

同样的流水线阶段也以只读诊断形式提供：`frame`、`screen`、`select`、`validate`、`freeze`、`review`、`signoff` 和 `compliance`。它们复用 `audit` 所使用的评估器；不构成另一条发布路径。

`capability` 校验已固定的能力/来源注册表。带上 `--capability` 和 `--provider` 时，它只返回有界的适配器清单；外部提供方可以提供知识或评审发现，但不能选择模型、冻结结果或宣布发布成功。该命令从不执行外部仓库代码。

使用 `mathmodel migrate PROJECT --dry-run --json` 可预览 v1 核心工件迁移；省略 `--dry-run` 则将 `artifacts/` 下的 v1 JSON 文件升级为 v2。JSONL 账本不会被重写，其只追加历史保持完整。

`package` 命令会阻止未解决的人工评审、缺失证据、未通过的质量/页数门控、过期或缺失的 PDF 以及缺失哈希的情况。PDF 总页数永远不能替代实质正文页数。

在正式竞赛模式下，`run` 具有人工检查点感知：`build` 前需要 H1、H2 已签核，`audit` 前需要 H3 已签核，`package` 前需要 H4 已签核。阻塞将以 `BLOCKED_HUMAN_INPUT` 报告；research 模式保留传统的自主编排行为。

`--profile cumcm` 和 `--mode` 选项是单次运行覆盖。它们从不重写项目配置；可接受的模式为 `research-autonomous`、`competition-assisted` 和 `competition-max`。编排器将所选模式传播给每个子 `build`、`audit`、`package` 阶段，因此正式覆盖不会静默回退到磁盘上的 research 模式。

`init` 与 `adopt` 接受相同的 profile/mode 选择用于新项目元数据，并创建 `CUMCM-WORKFLOW.md`。既有文件与既有配置均被保留；脚手架不会合成人工评审账本。

正式的人工评审记录同样与证据绑定：每条 `reviewed_artifacts` 路径必须是项目内相对且真实存在的文件，且每条 H1–H4 记录必须包含实质性的 `human_reasoning_summary` 以及非空的 `verified_points` 列表。绝对路径、路径穿越、缺失文件、过期时间戳、单纯的批准以及被拒绝的决定都无法通过检查点。

AI 使用记录以同样方式与证据绑定：每条 `output_artifacts` 条目必须指向项目内真实存在的文件，且 `accepted`、`human_modified`、`human_verified` 必须是真实的布尔字段。这防止账本声称评审过一个从未产生的工件。

确定性回归夹具位于 `mathmodel-skill/tests/fixtures/`，独立的 `competition_max` 集成夹具位于 `benchmarks/cases/formal-max-fixture/`。真实的 `traning1` 项目是一个集成示例：其配置的 build 会运行 `solve.py`、`enhance.py`、LaTeX 编译器、页数均衡门控、证据检查和发布打包。仓库保留了一份此前的已验证输出记录：总计 38 页、正文 32 页、附录 3 页；重新运行该验证需要可用的本地 TeX 安装。

在这台 Windows 工作区上，该示例使用 `traning1/mathmodel.json` 中内置的 Python 运行时路径，因为系统 Python 不含 `solve.py` 所需的数值与绘图依赖。将项目迁移到其他机器时，请将其中解释器路径替换为包含 NumPy、SciPy、Matplotlib 和 OpenPyXL 的 Python 环境。

## 执行与严谨模式

`execution_mode` 控制竞赛门控是否生效：`research_autonomous` 将竞赛专属门控报告为不适用，而 `competition_assisted` 与 `competition_max` 要求正式的证据链与人工签核链。

`rigor` 仅控制模型锦标赛搜索广度，默认为 `standard`：

- `fast`：至少一条基线加一条备选路线，适合时间有限的探索；
- `standard`：CUMCM profile 默认值（共 4 个候选、3 条非基线路线）；
- `max`：使用配置的 profile 上限，并保留最宽的评审预算。

三种模式均保留相同的风险探针、泄露、校验、可复现性、引用、AI 账本与人工门控要求。所选模式与生效上限会记录在 G2/G3 报告中以便审计。

新项目使用配置 Schema v2。既有 v1 配置会被接受并在内存中规范化，不修改原文件，保持与历史夹具和训练项目的向后兼容。

正式的 G8 评审还要求有结果/校验引用支撑的独立创新性评估；仅使用更新的算法不被视为创新。

`competition_max` 额外要求 `artifacts/competition-max-review.json`，记录至少 2 个模型侦察、4 条候选路线、3 类健壮性攻击、2 轮红队以及一次完成的 ARS 评审的唯一结构化记录。数量与攻击覆盖由这些记录推导而来，不被当作自由填写的整数或名称。`competition_assisted` 不要求该扩展工件。

正式校验还要求 `artifacts/experiment-registry.json`；其记录将运行与代码、输入、配置、种子、环境、指标、图表和结果工件绑定，哈希由本地评估器重新计算。

在 G9，发布哈希条目会针对当前项目文件独立重算；伪造的 `PASS`、过期摘要、重复路径或不安全路径都会阻止提交。

G9 还将质量报告与其当前源清单和可复现性摘要绑定，包括当前配置哈希。

质量报告提供两张互补的记分卡。`dimensions` 保留用于发布决策的八维内部门控评分，并报告显式评估状态：`ASSESSED_PASS`、`ASSESSED_FAIL`、`UNASSESSED` 或 `NOT_APPLICABLE`。`official_judge_view` 将同一证据映射到面向 CUMCM 的四个维度——模型合理性（30）、建模创造性（20）、结果正确性与可信度（30）、表达清晰度（20）。该映射仅用于诊断，不会削弱硬性门控。特别是，在记录到有证据支撑的、针对创新性的人工评估之前，创造性保持 `UNASSESSED`；算法名称或华美的文字不被视为创新证明。
