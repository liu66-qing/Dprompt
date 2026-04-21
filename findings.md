# Findings

## [2026-04-21 21:46 UTC] Phase 2.4 T2 confirmation verdict

- Context:
  - fixed-budget
  - freeze-A2
  - full `14` test items
  - seeds `42 / 43 / 44`
- Intended claim under active review:
  - `T2 = HSF-only` 是否已经足够稳定，可以正式成为当前唯一主方法
- Verdict:
  - `claim_supported = partial` `[pending external review]`

### What the results support

- `T2` 在 `3` 个 seeds 上的 `Dice@5` 均为正增益
- `NoC@90` 的均值优于 `T0`
- latency 没有变差
- memory 只小幅上升
- 这已经足够支持项目主线正式收缩到 `T2`

### What the results do not support

- 不支持继续把 `T3` 写成主方法
- 不支持把 `Adapter + HSF` 写成互补组合
- 不支持现在就写成强泛化论文 claim

### Missing evidence

- `T0 vs T2` 的 small-target / boundary 诊断
- 更明确的 paper-ready efficiency defense 组织

### Suggested claim revision

把当前主张改写成：

> 在当前 BTCV sample、freeze-A2、fixed-budget 的设定下，`T2 = HSF-only` 是当前唯一稳定的增量方法候选。

### Routing

- `T2`：继续
- `T3`：封存
- 下一步：只做 `T0 vs T2` 的诊断与论文叙事收束

## [2026-04-21 22:40 UTC] Phase 2.5 T2 diagnosis and defense verdict

- Context:
  - `T0 vs T2`
  - `3`-seed confirmed checkpoints
  - target-level local diagnosis
  - efficiency defense
  - representative cases
- Intended claim under active review:
  - `T2 = HSF-only` 是否已经具备可 defend 的主方法证据，而不只是平均数更好
- Verdict:
  - `claim_supported = yes (within current project scope)` `[pending external review]`

### What the results support

- `T2` 维持了全局 `Dice@5` 正增益
- latency 和 wall-clock per case 都优于 `T0`
- 当前最干净的局部信号来自 complex-boundary objects：
  - `Mean Delta Dice@5 = +0.0190`
  - `Median Delta Dice@5 = +0.0006`
  - `Win Rate = 59.5%`
- representative cases 已经把 success / tie / failure 都具体化

### What the results do not support

- 不支持把 small-target 写成 uniform uplift
- 不支持泛化到当前 BTCV sample 之外的更强 claim

### Missing evidence

- 论文文本层面的 claim wording freeze
- 主文 / appendix 里图表与叙事的最终摆放

### Suggested claim revision

把当前主张写成：

> 在当前 BTCV sample、freeze-A2、fixed-budget 的设定下，`T2 = HSF-only` 是一个可 defend 的轻量 bridge；其收益最清晰地集中在 boundary complexity 更高的结构上，同时保持了合理的效率代价。

### Routing

- `T2`：保留为唯一主方法
- `T3`：继续封存
- 下一步：停止新实验，进入 paper-ready claim freeze
