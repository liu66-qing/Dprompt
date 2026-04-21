# Phase 2：B 系最小增强 Run（已封存）

> 这个文档只保留历史实现背景。当前活动主线已经在 Phase 2.4 正式收缩为 `T2 = HSF-only`，`T3` 不再作为主方法目标。

## 这份历史文档曾经回答什么

它最初用来验证：

- `B0 / B1 / B2 / B3` 的 wiring 是否干净
- `B0` 是否仍等于 `A2`
- `Local Adapter`、`HSF`、以及它们的组合是否值得继续

## 现在已经确认的历史结论

- `B0 / B1 / B2 / B3` 的 zero-perturbation wiring 是干净的
- `T2 = HSF-only` 是当前唯一稳定的正向 bridge 信号
- `T3 = Adapter + HSF` 在 fixed-budget full-14 下没有形成互补

## 当前如何使用这份文档

- 把它当成实现背景和历史对照
- 不再把其中的 `B3` 叙事当成活动主线
- 不再从这里继续发散到 `B4`、`T3 rescue` 或 adapter 扩展

## 当前活动主线在哪里

请改看：

- `claim_driven实验路径.md`
- `refine-logs/EXPERIMENT_PLAN.md`
- `refine-logs/EXPERIMENT_TRACKER.md`
- `docs/Phase2_4_T2Confirmation.md`
