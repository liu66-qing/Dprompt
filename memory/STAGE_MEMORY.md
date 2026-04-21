# 阶段记忆文档

> 目标：每完成一个阶段，就把已确认事实、已完成动作、阻碍、下一步压缩记录到这里，下一次可以直接续跑。

## [2026-04-21 05:52:49 UTC] 阶段 0.1：项目梳理与环境勘测

### 已确认
- `Dprompt` 当前主要是实验规范仓库，不包含 IMIS-Bench 主体代码；核心文件是主规划、实验启动记录、变更记录、数据路径规范和统一启动脚本。
- `configs/paths.local.yaml` 必须为本地真实路径配置，不能提交到 Git。
- `scripts/run_experiment.sh` 已提供统一实验启动和记录模板。

### 本机环境
- 工作目录：`/root/autodl-tmp/jiujiu/Dprompt`
- Python：`3.12.3`
- Conda：`24.4.0`
- Node：`v20.20.2`
- NPM：`10.8.2`
- GPU：`NVIDIA GeForce RTX 5090 32GB`
- 可用磁盘：约 `50G`

### 远程资源确认
- IMIS-Bench README 已确认官方推荐环境：`Python 3.8.19 + CUDA 11.8 + PyTorch 2.2.1`
- IMIS-Bench 主数据是 Hugging Face 上的 `IMed-361M`，仓库内只带 demo/sample 数据
- ARIS（`Auto-claude-code-research-in-sleep`）仓库已同步到本地，skills 与 MCP 模板可用

### 已完成动作
- 创建了目录：
  - `external/`
  - `data/`
  - `envs/`
  - `memory/`
- 读取并理解了主规划、实验记录、变更记录和本地规范文档
- 确认 GitHub 长连接不稳定，改为按目录树精准同步所需文件

### 下一步
- 同步 IMIS-Bench 与 ARIS 关键内容到 `external/`
- 创建 IMIS-Bench 专用环境
- 建立本地路径配置并做 smoke check

## [2026-04-21 09:23:45 UTC] 阶段 0.2：IMIS-Bench 环境打通与 1-batch smoke 通过

### 已确认
- `external/IMIS-Bench/dataset/BTCV` 已补齐完成：
  - 文件数：`601`
  - 大小：约 `419 MB`
- IMIS-Bench 当前本机可运行环境：
  - conda 前缀：`/root/autodl-tmp/jiujiu/Dprompt/envs/imisbench`
  - Python：`3.10`
  - PyTorch：`2.11.0+cu128`
  - torchvision：`0.26.0+cu128`
  - transformers：`4.39.3`
  - monai：`1.5.1`
  - timm：`0.9.16`
- checkpoint 已接到：
  - `external/IMIS-Bench/ckpt/IMISNet-B.pth`
- ARIS 接入状态：
  - 全局 Codex skills 已装入 `~/.codex/skills`
  - 项目级 `.agents/skills/` 已创建本地 symlink 入口
  - MCP bridge 模板已同步，但 reviewer MCP 仍缺 CLI / API 凭证

### 已完成动作
- 修复 `scripts/github_snapshot_sync.py` 的 raw URL 编码问题
- 创建并安装 IMIS-Bench 环境：
  - `envs/imisbench`
- 新建并补齐项目规范文件：
  - `AGENTS.md`
  - `configs/paths.example.yaml`
  - `configs/paths.local.yaml`
  - `docs/ARIS_Codex_接入说明.md`
  - `scripts/setup_aris_mcp.sh`
  - `scripts/imisbench_smoke.py`
- 修改 IMIS-Bench 代码以支持离线 smoke：
  - `model.py` 中 tokenizer 改为按需加载
  - `test.py` 仅在 `prompt_mode=text` 时生成 text prompt

### Smoke 结果
- 数据读取成功
- checkpoint 加载成功
- 1-batch 前向成功
- Phase 0 的“本机最小可运行链路”已打通

### 当前阻碍
- reviewer MCP 尚未可用
- `text` prompt 路径仍需要可访问的 tokenizer 源或本地 tokenizer 目录

### 下一步
- 跑一次更接近官方入口的 `points` 评测
- 开始 A0 / A1 / A2 baseline legalization

## [2026-04-21 09:26:23 UTC] 阶段 0.3：官方 `test.py` points 模式跑通

### 已确认
- `external/IMIS-Bench/test.py` 已可在单卡 `cuda:0` 下直接运行
- 单卡模式日志文件已正常生成在：
  - `external/IMIS-Bench/work_dir/ft-IMISNet/points_output_2026-04-21-17-25-52.log`

### 已完成动作
- 为 `external/IMIS-Bench/train.py` 和 `external/IMIS-Bench/test.py` 补上单卡日志初始化
- 使用官方入口完成 `points` 模式 sample 评测

### 结果摘要
- sample 数据集共跑完 `14` 个 test item
- `Image Avg Dice = 0.8314`

### 下一步
- 对照主规划进入 A0 / A1 / A2 baseline legalization

## [2026-04-21 09:39:00 UTC] 阶段 1.1：A0 / A1 / A2 baseline legalization 已在 sample 上完成

### 已确认
- 已新增 Phase 1 基线定义文件：
  - `configs/phase1_baselines.yaml`
- 已新增统一 legalization 脚本：
  - `scripts/phase1_baseline_eval.py`
- 已新增说明文档：
  - `docs/Phase1_A2基线合法化.md`

### A0 / A1 / A2 当前本地定义
- `A0`：
  - `points + K=1`
- `A1`：
  - `{points, bboxes} x {1, 3, 5, 8}`
- `A2`：
  - `points + K=8`
  - 当前冻结为后续唯一强基线 `B0`

### sample legalization 结果摘要
- `A0 points K=1`：
  - Dice `0.8314`
- `A1 points K=3 / 5 / 8`：
  - `0.8735 / 0.8913 / 0.8885`
- `A1 bboxes K=1 / 3 / 5 / 8`：
  - `0.8970 / 0.9060 / 0.9195 / 0.9124`
- `A2 points K=8`：
  - Dice `0.8885`
  - IoU `0.8223`
  - avg sample latency `0.9015 s`
  - peak memory `4451.8 MB`

### 当前结论
- A2 已明显强于 A0，满足“先立住合法基线再做方法”的基本要求
- points 分支在 `K=1 -> 3 -> 5` 持续上升，`K=8` 有轻微回落，说明 sample 上存在后期饱和
- bbox 分支整体更强，应保留为 supporting upper-bound

### 结果文件
- `results/phase1_baselines/LATEST_phase1_baselines.json`
- `results/phase1_baselines/LATEST_phase1_baselines.csv`
- `results/phase1_baselines/LATEST_phase1_baselines.md`

### 下一步
- 当前活动主线已重置为：
  - Late-Stage Local Adapter
  - Hierarchical Semantic Fusion
  - optional Light Prompt-Aware Weighting

## [2026-04-21 12:05:00 UTC] 阶段 2.0：旧 contract 线已停用，当前活动主线切换为 B 线增强方案

### 已确认
- 上一轮交互重解释主线已判停，不再作为当前论文叙事的一部分
- 活动文档中相关失败记录已清理：
  - 旧 `Phase 2 / 2.5` 文档与活动日志已移除
- 当前活动主线已冻结为：
  - `B0 = A2 baseline`
  - `B1 = B0 + Late-Stage Local Adapter`
  - `B2 = B0 + Hierarchical Semantic Fusion`
  - `B3 = B0 + Local Adapter + HSF`
  - `B4 = B3 + Light Prompt-Aware Weighting`（optional）

### 已完成动作
- 使用 `experiment-plan` 思路新增：
  - `refine-logs/EXPERIMENT_PLAN.md`
  - `refine-logs/EXPERIMENT_TRACKER.md`
- 新增当前阶段文档：
  - `docs/Phase2_B系最小增强Run.md`
- 重写主规划：
  - `claim_driven实验路径.md`
- 更新项目操作约定：
  - `AGENTS.md`

### 当前实现落点
- `external/IMIS-Bench/segment_anything/modeling/image_encoder.py`
  - 后段 adapter
  - 多层 token taps
- `external/IMIS-Bench/model.py`
  - `image_forward`
  - `forward_decoder`
  - 多层特征的 encoder / decoder 交接
- `external/IMIS-Bench/segment_anything/modeling/mask_decoder.py`
  - Hierarchical Semantic Fusion
  - optional prompt-aware weighting

### 当前阻碍
- 新 B 线仍未实现
- 当前首要风险不是指标，而是：
  - 多层 feature taps 与 decoder 融合接口改造是否能在不伤 B0 的前提下顺利接通

### 下一步
- 按 `refine-logs/EXPERIMENT_TRACKER.md` 先做：
  - `R001` sanity：feature taps / adapter reshape / decoder 接口打通
  - `R002` baseline freeze：确认 B0 继续等于 A2
  - `R003-R005`：B1 / B2 / B3 最小矩阵

## [2026-04-21 20:41:00 UTC] 阶段 2.1：B 线最小实现已打通，B0 冻结确认完成

### 已确认
- 当前 B 线实现入口已冻结为：
  - `configs/phase2_b_methods.yaml`
  - `scripts/phase2_b_minimal_eval.py`
- `external/IMIS-Bench` 中 B 线相关接口已接通：
  - `image_encoder.py` 可选输出后段 adapter 与 hierarchical embeddings
  - `model.py` 已兼容 tensor / dict 两类 image embedding
  - `build_sam.py` 可按方法配置注入 `local_adapter_blocks / hsf_blocks`
- `R001` smoke 已全部通过：
  - `B0 / B1 / B2 / B3` 都能完成 1-batch 前向
  - `B2 / B3` 的 hierarchical embeddings 已能进入 decoder
- `R002` baseline freeze 已通过：
  - 当前 `B0 avg_dice = 0.889020`
  - 历史 `A2 avg_dice = 0.888547`
  - `delta = +0.000473`
  - 当前 `B0 avg_iou = 0.823460`
  - 历史 `A2 avg_iou = 0.822264`
  - `delta = +0.001196`
- `R003-R005` 首轮 full-run 已完成，当前统一 evaluator 结果为：
  - `Dice@3 = 0.8627`
  - `Dice@5 = 0.8794`
  - `Dice@8 = 0.8890`
  - `NoC@90 = 5.143`
  - `B1 / B2 / B3` 当前与 `B0` 完全等价

### 已完成动作
- 以 `experiment-bridge` 的实现-验证顺序完成：
  - B 线配置冻结
  - smoke
  - 1-case sanity
  - B0 freeze
  - B0/B1/B2/B3 full-run
- 以 `analyze-results` 口径完成首轮结果整理并落盘到：
  - `results/phase2_b_minimal/LATEST_phase2_b_minimal.json`
  - `results/phase2_b_minimal/LATEST_phase2_b_minimal.csv`
  - `results/phase2_b_minimal/LATEST_phase2_b_minimal.md`

### 结果解释
- 当前 `B1 / B2 / B3 == B0` 是预期现象，不是实现失败：
  - `LateStageLocalAdapter` 走 zero-init residual 路径
  - `HierarchicalSemanticFusion` 的 level weights 初始化为 `0`
  - 这说明当前阶段已经验证“新增模块不会污染基线”，但还没有进入“可学习增益”阶段
- checkpoint 加载中出现的新模块 `missing_keys` 是预期的：
  - 旧 checkpoint 不含新增 adapter / HSF 参数
  - 目前通过 `strict=False` 合法接入

### 当前阻碍
- 现在继续扩 `B4`、small-target、boundary 或多 seed 都没有信息增量
- 在没有训练或参数激活策略之前，`B1 / B2 / B3` 不可能表现出真正方法差异

### 下一步
- 不要横向扩表
- 进入更小的 `Phase 2.2`：
  - 只设计一个最小 trainable bridge
  - 优先考虑冻结 backbone，仅训练新增 Local Adapter / HSF 相关参数
  - 先验证 `B3` 能否从“零扰动等价”变成“有可测增益”

## [2026-04-21 21:10:00 UTC] 阶段 2.2：Trainable Bridge 已通过最小可学习性验证

### 已确认
- `Phase 2.2` 当前唯一问题已被单独拉出来验证：
  - 冻结 `A2`
  - 只训练 bridge 参数
- 当前配置文件已新增：
  - `configs/phase2_2_trainable_bridge.yaml`
  - `configs/phase2_2_bridge_eval.yaml`
- 当前最小运行矩阵：
  - `T0 = B0-frozen`
  - `T1 = Adapter-only`
  - `T2 = HSF-only`
  - `T3 = Adapter + HSF`

### 已完成动作
- 新增 bridge 参数边界审计脚本：
  - `scripts/phase2_2_bridge_audit.py`
- 在 `IMISNet` 中新增 trainable scope 控制：
  - `none`
  - `adapter_only`
  - `hsf_only`
  - `bridge_only`
- 在 `train.py` 中加入最小 bridge-only 训练开关：
  - `disable_text_prompt`
  - `skip_interaction_training`
  - `max_steps_per_epoch`
- evaluator 已支持读取训练态 wrapper checkpoint，并回填整模型权重

### 关键结构发现
- `HSF` 分支本来就是可学习的：
  - `T2/T3` 的 `hsf_module.level_weights` 已离开零点
- 原始 `Local Adapter` 初始化会堵死梯度：
  - 原因是 `depthwise=0` 且 `pointwise=0`
- 已做最小修复：
  - `depthwise` 改为 identity-like
  - `pointwise` 保持 `0`
  - 这样初始输出仍为 `0`，但梯度可以进入 pointwise 分支

### 当前最小证据
- 参数审计：
  - `T0 = 0`
  - `T1 = 1,790,208`
  - `T2 = 17,703,939`
  - `T3 = 19,494,147`
- 短训后参数已离开初始化：
  - `T1 adapter_norm = 83.17`
  - `T2 level_weights abs sum = 1.17e-05`
  - `T3 adapter_norm = 83.18`
  - `T3 level_weights abs sum = 4.51e-05`
- 2-case smoke eval：
  - `T0 Dice@5 = 0.8330`
  - `T1 Dice@5 = 0.8562`
  - `T2 Dice@5 = 0.8664`
  - `T3 Dice@8 = 0.8890`

### 当前结论
- Phase 2.2 的 bridge learnability gate 已初步通过：
  - `HSF` 已确认可学
  - `Adapter` 在修复初始化后已确认可学
  - `T3` 组合桥接层可学且未出现明显破坏性退化
- 当前结果仍然只是：
  - 最小 smoke
  - 结构性可学习性验证
- 当前结果还不是：
  - 主文表
  - full-sample 结论
  - 多 seed 结论

### 下一步
- 继续克制，不横向扩
- 只把当前 Phase 2.2 放大为一个固定小预算 bridge-only run：
  - 保持 freeze-A2
  - 保持 `disable_text_prompt`
  - 保持 `skip_interaction_training`
  - 在 full `14` 个 test item 上复核 `T1/T2/T3`

## [2026-04-21 21:29:00 UTC] 阶段 2.3：Fixed-Budget Full-14 Bridge Validation 已完成

### 已确认
- 当前 Phase 2.3 严格沿用 Phase 2.2 的 fixed-budget checkpoint：
  - 不重训
  - 不改 recipe
  - 只把评测从 `2-case smoke` 放大到 full `14`
- 当前 full-14 结果文件：
  - `results/phase2_3_full14_bridge_eval/LATEST_phase2_b_minimal.json`
  - `results/phase2_3_full14_bridge_eval/LATEST_phase2_b_minimal.csv`
  - `results/phase2_3_full14_bridge_eval/LATEST_phase2_b_minimal.md`
- 当前阶段文档：
  - `docs/Phase2_3_FixedBudgetFull14.md`

### Full-14 主结果
- `T0`：
  - `Dice@5 = 0.8794`
  - `Dice@8 = 0.8890`
  - `NoC@90 = 5.143`
- `T1`：
  - `Dice@5 = 0.8813`
  - `Dice@8 = 0.8965`
  - `NoC@90 = 5.071`
- `T2`：
  - `Dice@5 = 0.8906`
  - `Dice@8 = 0.8900`
  - `NoC@90 = 4.786`
- `T3`：
  - `Dice@5 = 0.8663`
  - `Dice@8 = 0.8874`
  - `NoC@90 = 5.929`

### Delta vs T0
- `T1`：
  - `Dice@5 +0.0019`
  - `Dice@8 +0.0075`
  - `NoC@90 -0.071`
- `T2`：
  - `Dice@5 +0.0112`
  - `Dice@8 +0.0009`
  - `NoC@90 -0.357`
- `T3`：
  - `Dice@5 -0.0130`
  - `Dice@8 -0.0016`
  - `NoC@90 +0.786`

### Win Rate vs T0
- `Dice@5`
  - `T1 = 3 win / 11 loss`
  - `T2 = 8 win / 6 loss`
  - `T3 = 4 win / 10 loss`
- `Dice@8`
  - `T1 = 7 / 7`
  - `T2 = 8 / 6`
  - `T3 = 8 / 6`

### 当前结论
- B 线没有被否掉：
  - full-14 下至少 `T2` 仍然清晰优于 `T0`
- 当前最可信的正向信号来自：
  - `HSF-only`
- `Adapter-only` 是弱正向：
  - 均值有提升
  - 但 `Dice@5` win rate 不够强
- `Adapter + HSF` 当前没有形成互补：
  - `T3` 弱于 `T2`
  - 当前不能支持“组合桥已经成立”的说法

### Go / No-Go 判断
- bridge-only 路线：
  - `GO`
- 当前 `T3` 组合作为主方法：
  - `NO-GO / not yet`

### 下一步
- 不做 `B4`
- 不做多 seed
- 不做 small-target / boundary
- 不解冻 backbone
- 如果继续，只能沿当前线收紧：
  - 优先围绕 `T2` 和 `T3` 的差异做下一步最小诊断

## [2026-04-21 21:46:00 UTC] 阶段 2.4：T2 Confirmation Run 已完成，主方法正式收缩为 T2

### 已确认
- `Phase 2.4` 只保留：
  - `T0 = A2 / B0-frozen`
  - `T2 = HSF-only`
- 固定条件没有变化：
  - freeze-A2
  - `disable_text_prompt = true`
  - `skip_interaction_training = true`
  - `trainable_scope = hsf_only`
  - `hsf_blocks = [9, 10, 11]`
  - fixed budget = `1 epoch + 2 steps/epoch`
- 当前确认 run 已在 full `14` test items 和 `3` 个 seeds 下完成：
  - `42`
  - `43`
  - `44`

### 3-seed 汇总结果
- `T0`：
  - `Dice@5 = 0.8768 +- 0.0077`
  - `Dice@8 = 0.8884 +- 0.0029`
  - `NoC@90 = 5.333 +- 0.330`
  - latency `= 0.1253 +- 0.0024 s`
  - memory `= 3540.2 +- 23.1 MB`
- `T2`：
  - `Dice@5 = 0.8866 +- 0.0042`
  - `Dice@8 = 0.8884 +- 0.0062`
  - `NoC@90 = 5.190 +- 0.393`
  - latency `= 0.1192 +- 0.0010 s`
  - memory `= 3752.1 +- 20.1 MB`

### Delta vs T0
- `Dice@5 = +0.0098 +- 0.0062`
- `Dice@8 = +0.0000 +- 0.0040`
- `NoC@90 = -0.143 +- 0.214`
- latency：
  - 约 `-4.9%`
- memory：
  - 约 `+6.0%`

### 更关键的结构性结论
- `Dice@5` 在 `3` 个 seed 上全部翻正：
  - seed `42`: `+0.0119`
  - seed `43`: `+0.0148`
  - seed `44`: `+0.0028`
- `NoC@90` 在 `3` 个 seed 中有 `2` 个更好，均值也更好
- pooled win rate：
  - `Dice@5 = 23 win / 17 loss / 2 tie`
  - `Dice@8 = 26 win / 16 loss / 0 tie`

### 当前判定
- 旧主张：
  - `T3 = Adapter + HSF` 是主方法
  - 结论：不支持，正式封存
- 当前缩窄主张：
  - `T2 = HSF-only` 是当前唯一稳定的主方法候选
  - 结论：支持继续推进
- 更准确地说：
  - 这已经足够支持项目主线正式切到 `T2-only`
  - 但对论文级泛化主张仍然只算 partial support

### 已完成动作
- 新增阶段文档：
  - `docs/Phase2_4_T2Confirmation.md`
- 重写活动规划：
  - `claim_driven实验路径.md`
  - `refine-logs/EXPERIMENT_PLAN.md`
  - `refine-logs/EXPERIMENT_TRACKER.md`
- 新增本地 findings：
  - `findings.md`
- 将 `docs/Phase2_B系最小增强Run.md` 改写为封存说明，避免后续误回到 `B3` 主线

### 现在不要再做什么
- 不做 `T3` rescue
- 不做 `G1 / G2 / G3`
- 不做 adapter 范围缩放
- 不做 staged training
- 不做新 loss
- 不做 `B4`
- 不做 backbone 解冻

### 下一步
- 当前没有启动新实验
- 如果继续，只允许沿 `T0 vs T2` 往前：
  - small-target / boundary 诊断
  - efficiency defense
  - 论文叙事收束

## [2026-04-21 22:40:00 UTC] 阶段 2.5：T2-only Diagnosis and Defense 已完成

### 已确认
- 当前 Phase 2.5 严格只看：
  - `T0 = A2 / B0-frozen`
  - `T2 = HSF-only`
- 没有新增训练，也没有新增方法分支
- 当前 analysis unit 使用：
  - `image_root + target_name`
  - 即 target-level object
- 当前本阶段输出：
  - `results/phase2_5_t2_diagnosis/LATEST_phase2_5_t2_diagnosis.md`
  - `results/phase2_5_t2_diagnosis/LATEST_phase2_5_t2_diagnosis.json`
  - `figures/phase2_5_t2_performance_cost.pdf`
  - `figures/phase2_5_t2_representative_cases.pdf`

### Efficiency defense 结果
- `Delta Dice@5 = +0.0098 +- 0.0062`
- `Delta Dice@8 = +0.0000 +- 0.0040`
- `Delta NoC@90 = -0.143 +- 0.214`
- `Delta Avg Interaction Latency = -0.0061 +- 0.0014 s`
- `Delta Wall-clock / case = -0.0486 +- 0.0110 s`
- `Delta Peak Memory = +211.9 +- 6.8 MB`

### Local diagnosis 结果
- 尺寸分层：
  - `small`：
    - `Mean Delta Dice@5 = +0.0144`
    - `Median Delta Dice@5 = -0.0008`
    - `Win Rate = 37.9%`
  - `medium`：
    - `Mean Delta Dice@5 = +0.0167`
    - `Median Delta Dice@5 = +0.0003`
    - `Win Rate = 57.1%`
  - `large`：
    - `Mean Delta Dice@5 = +0.0014`
    - `Median Delta Dice@5 = +0.0009`
    - `Win Rate = 60.7%`
- 边界复杂度分层：
  - `simple`：
    - `Mean Delta Dice@5 = +0.0030`
    - `Median Delta Dice@5 = -0.0002`
    - `Win Rate = 44.2%`
  - `complex`：
    - `Mean Delta Dice@5 = +0.0190`
    - `Median Delta Dice@5 = +0.0006`
    - `Win Rate = 59.5%`

### 这阶段最重要的解释
- 当前最干净、最可 defend 的证据来自：
  - **complex boundary objects**
- small-target 只算部分支持：
  - 均值是正的
  - 但 median 为负，win rate 也不高
- 因此后续论文叙事不能写成：
  - “`T2` 对 small targets 一致提升”
- 更合适的写法是：
  - `T2` 的收益更集中在 boundary complexity 更高的结构上
  - 对 small targets 的帮助存在，但更像 concentrated gains

### Representative cases
- 已固定 `4` 类：
  - small-target win
  - complex-boundary win
  - near tie
  - failure case
- 当前定性图使用：
  - 代表 seed `42`
  - 选择依据是 `3`-seed mean

### 当前 verdict
- `T2` 已不再只是“均值翻正的候选方法”
- 当前已经具备：
  - 主方法稳定性
  - 效率 defense
  - 局部诊断
  - representative cases
- 因此项目路由上：
  - **停止新实验**
  - 进入 paper-ready claim freeze

### 现在不要再做什么
- 不回到 `T3`
- 不做 `B4`
- 不做新 loss / 新模块
- 不做新的横向方法比较
- 不为了 small-target story 再开补救实验

### 下一步
- 不再开实验
- 直接进入：
  - main table / diagnosis table 定稿
  - figure 摆放
  - claim wording freeze
