# Experiment Plan

**Problem**: 在强 `A2` 基线上，ViT-based IMIS 的 decoder 仍可能缺少足够稳的后段分层语义利用，导致局部区域的修正效率提升不稳定。  
**Method Thesis**: 不重写交互机制，只保留 `T2 = HSF-only` 作为轻量 trainable bridge，验证它能否在冻结 `A2` 的前提下稳定带来增量。  
**Date**: 2026-04-21

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|-----------------|-----------------------------|---------------|
| C1: `T2 = HSF-only` 是当前唯一稳定的 bridge 增量 | 这是当前唯一主方法命题 | full-14、3-seed 下 `Dice@5` 平均优于 `T0`，且 `NoC@90` 均值不差于 `T0` | Block 3 |
| C2: `T2` 的收益不是靠破坏效率换来的 | reviewer 会先质疑 cost trade-off | latency 不升，Peak Memory 仅小幅增加 | Block 3, Block 4 |
| C3: `T2` 的增益应更贴近局部结构表达，而不是偶然均值波动 | 这是后续 paper defense 的核心解释 | 在 boundary-complexity 诊断上对 `T0` 有更清晰收益；small-target 只部分支持 | Block 4 |
| Anti-claim: `T3` 组合桥才是主方法 | 这是当前最需要主动切掉的错误叙事 | `T3` 在 full-14 fixed-budget 下弱于 `T2`，因此应归档而非继续 rescue | Block 2, Block 3 |

## Paper Storyline

- Main paper currently supports:
  - `A2` 是唯一合法强基线
  - `T2 = HSF-only` 是当前唯一稳定主方法候选
  - `T2` 的 fixed-budget 增量在 3 seeds 上可重复
  - 效率代价可控
- Appendix or background only:
  - `B0/B1/B2/B3` 的 zero-perturbation wiring
  - `T1/T3` 的 learnability 历史
  - `T3` 为什么失败的实现背景
- Experiments intentionally cut:
  - `T3` rescue
  - `B4` prompt-aware weighting
  - adapter 范围扩展
  - staged training
  - backbone unfreeze
  - 旧 contract / trigger 主线

## Experiment Blocks

### Block 1: Baseline Anchor

- Claim tested:
  - 所有增强都必须锚定在 `A2`
- Why this block exists:
  - 锁死唯一参照面，避免配置漂移
- Dataset / split / task:
  - BTCV sample proxy，interactive segmentation
- Compared systems:
  - A0, A1, A2
- Metrics:
  - Dice@1/3/5/8, latency, Peak Memory
- Setup details:
  - 已完成，`A2 = points, K=8`
- Success criterion:
  - `A2` 继续作为唯一 `T0`
- Status:
  - DONE

### Block 2: Bridge Hygiene and Learnability

- Claim tested:
  - 新 bridge 路径不会污染基线，而且 `HSF` 确实能学到非零增量
- Why this block exists:
  - 先把工程闭环和可学习性单独证明出来
- Dataset / split / task:
  - BTCV sample proxy
- Compared systems:
  - `B0/B1/B2/B3`
  - `T0/T1/T2/T3`
- Metrics:
  - zero-perturbation 一致性
  - trainable param audit
  - 2-case smoke Dice / NoC
- Setup details:
  - `freeze-A2`
  - `disable_text_prompt = true`
  - `skip_interaction_training = true`
- Success criterion:
  - `T2` bridge 参数离开初始化且不出现破坏性退化
- Status:
  - DONE

### Block 3: Fixed-Budget Full-14 Main Validation

- Claim tested:
  - `T2` 在完整 `14` 个 test items 和 `3` 个 seeds 下仍是稳定正向信号
- Why this block exists:
  - 这是当前主方法是否成立的最小确认 gate
- Dataset / split / task:
  - BTCV full `14` test items
- Compared systems:
  - `T0`
  - `T2`
- Metrics:
  - Dice@5
  - Dice@8
  - NoC@90
  - Avg Interaction Latency
  - Peak Memory
  - pooled win rate vs `T0`
- Setup details:
  - fixed budget：`1 epoch + 2 steps/epoch`
  - seeds：`42, 43, 44`
  - `trainable_scope = hsf_only`
  - `hsf_blocks = [9, 10, 11]`
- Success criterion:
  - `Dice@5` 平均翻正，且效率代价可控
- Result snapshot:
  - `T2 Dice@5 = 0.8866 +- 0.0042`
  - `T0 Dice@5 = 0.8768 +- 0.0077`
  - `Delta Dice@5 = +0.0098 +- 0.0062`
  - `Delta NoC@90 = -0.143 +- 0.214`
  - latency 约 `-4.9%`
  - memory 约 `+6.0%`
- Status:
  - DONE

### Block 4: Local Diagnosis and Efficiency Defense

- Claim tested:
  - `T2` 的收益更贴近小目标、边界或局部结构表达，而不是偶然均值波动
- Why this block exists:
  - 这是当前最值得做的 paper defense
- Dataset / split / task:
  - BTCV sample proxy
  - small-target subset 或 boundary-related subset
- Compared systems:
  - `T0`
  - `T2`
- Metrics:
  - subset Dice
  - boundary-related metric 或 small-target Dice
  - Avg Interaction Latency
  - Peak Memory
- Setup details:
  - 不改方法
  - 不改训练 recipe
  - 只做解释性诊断
- Success criterion:
  - 局部诊断上存在比整体均值更清晰的正向信号
- Failure interpretation:
  - `T2` 可能只是当前 sample 条件下的轻微均值优势
- Status:
  - DONE
- Result snapshot:
  - complex boundary:
    - `Mean Delta Dice@5 = +0.0190`
    - `Median Delta Dice@5 = +0.0006`
    - `Win Rate = 59.5%`
  - simple boundary:
    - `Mean Delta Dice@5 = +0.0030`
    - `Median Delta Dice@5 = -0.0002`
    - `Win Rate = 44.2%`
  - small targets:
    - `Mean Delta Dice@5 = +0.0144`
    - `Median Delta Dice@5 = -0.0008`
    - `Win Rate = 37.9%`
  - efficiency:
    - wall-clock per case `-0.0486 +- 0.0110 s`
    - Avg Interaction Latency `-0.0061 +- 0.0014 s`
    - Peak Memory `+211.9 +- 6.8 MB`
- Interpretation:
  - `T2` 的最干净增益来源是 boundary complexity，而不是 blanket small-target uplift

### Block 5: Paper-Ready Finalization

- Claim tested:
  - 当前缩窄 claim 是否已经足够进入写作
- Why this block exists:
  - 防止在主结论还不稳时过早扩表
- Compared systems:
  - `T0`
  - `T2`
- Deliverables:
  - main table
  - diagnosis table
  - claim wording freeze
- Trigger condition:
  - Block 4 已完成，可以进入论文定稿收束
- Status:
  - TODO

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Status |
|-----------|------|------|---------------|------|--------|
| M0 | baseline freeze | A0 / A1 / A2 | `A2` 合法化成功 | 低 | DONE |
| M1 | bridge hygiene | `B0/B1/B2/B3` wiring | 新路径不污染 `A2` | 低 | DONE |
| M2 | bridge learnability | `T0/T1/T2/T3` smoke | `T2` 可学 | 低 | DONE |
| M3 | main confirmation | `T0 vs T2`, 3 seeds, full-14 | `T2` 平均翻正且 cost 可控 | 中 | DONE |
| M4 | diagnosis | `T0 vs T2` local diagnosis | 收益来源可解释 | 中 | DONE |
| M5 | paper freeze | 表格、措辞、结构收束 | 只在 `M4` 过后启动 | 中 | TODO |

## Compute and Data Budget

- Current completed budget:
  - `3` 个 seeds
  - 每个 seed 为 `1 epoch + 2 steps/epoch`
  - full `14` eval
- Remaining budget should stay narrow:
  - 只允许 `T0 vs T2`
  - 不再为 `T3` 投入算力
- Biggest remaining bottleneck:
  - 如何把“complex boundary 更受益、small-target 只部分支持”写成足够克制但有说服力的 paper claim

## Risks and Mitigations

- 风险：
  - `T2` 的均值增益在更细分诊断里不明显
- 缓解：
  - 优先做 small-target / boundary 子集，而不是扩新模型

- 风险：
  - 重新被 `T3` 失败组合吸走注意力
- 缓解：
  - 所有活动文档都统一改为 `T2-only`

- 风险：
  - 过早写成泛化性过强的论文 claim
- 缓解：
  - 当前只保留 sample + fixed-budget 范围内的诚实表述

## Final Checklist

- [x] Main method has been narrowed to `T2`
- [x] `T3` has been archived
- [x] Fixed-budget 3-seed confirmation is complete
- [x] Efficiency cost is quantified
- [x] Local diagnosis is complete
- [ ] Paper-ready claim wording is frozen
