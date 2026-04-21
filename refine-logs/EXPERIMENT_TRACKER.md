# Experiment Tracker

> 当前活动记录只保留仍与 `T2-only` 主线直接相关的实验。

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|--------|-----------|---------|------------------|-------|---------|----------|--------|-------|
| R001 | M0-M1 | baseline anchor | `A0 / A1 / A2` legalization | BTCV sample | Dice@1/3/5/8, latency, Peak Memory | MUST | DONE | `A2 = points, K=8` 已冻结为唯一强基线 |
| R002 | M2.1 | bridge hygiene | `B0 / B1 / B2 / B3` zero-perturbation wiring | BTCV sample | freeze check, Dice@3/5/8, NoC@90 | MUST | DONE | wiring 干净；新增路径未污染 `A2` |
| R003 | M2.2 | bridge learnability | `T0 / T1 / T2 / T3` smoke | BTCV sample smoke | trainable param audit, 2-case Dice/NoC | MUST | DONE | `HSF` 可学；adapter 也可学，但这不构成保留 `T3` 的理由 |
| R004 | M2.3 | main validation | `T0 / T1 / T2 / T3` fixed-budget full-14 | BTCV full 14 test items | Dice@3/5/8, NoC@90, latency, memory, win rate | MUST | DONE | `T2` 是 clearest positive；`T3` 未过 gate，正式降级 |
| R005 | M2.4 | T2 confirmation | `T0 vs T2`, seeds `42/43/44` | BTCV full 14 test items | mean +- std of Dice@5/8, NoC@90, latency, memory, pooled win rate | MUST | DONE | `T2 Dice@5 +0.0098 +- 0.0062`，`NoC@90 -0.143 +- 0.214`，latency 更快，memory `+6.0%` |
| R006 | M3 | local diagnosis | `T0 vs T2` on small-target / boundary subset | BTCV sample | subset Dice, boundary metric, latency, memory | MUST | DONE | complex-boundary 信号最干净：`Mean Delta Dice@5 = +0.0190`，`Win Rate = 59.5%`；small-target 只部分支持 |
| R007 | M4 | paper freeze | `T0 vs T2` final table and claim wording | BTCV sample | main table, diagnosis table, final claim scope | MUST | TODO | 当前唯一合理下一步；不再新增实验，只收束正文与图表 |
