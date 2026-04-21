# Phase 2.3：Fixed-Budget Full-14 Bridge Validation

> 历史阶段文档。后续 Phase 2.4 已完成 `T2-only` 的 `3`-seed 确认，因此本文档现在只保留“为什么主线会收缩到 `T2`”的背景证据，不再作为活动规划。

## 目标

只回答一个问题：

> 在冻结 `A2`、固定小预算训练的前提下，`T1 / T2 / T3` 的 bridge 增量，能否在 full `14` 个 test items 上稳定优于 `T0`？

## 固定条件

本阶段没有改 recipe，只把评测从 smoke 放大到 full `14`：

- freeze-A2
- `disable_text_prompt = true`
- `skip_interaction_training = true`
- 当前 evaluator
- 当前 prompt protocol
- 当前 fixed-budget checkpoint

没有做：

- `B4`
- 多 seed
- small-target / boundary 分层
- 新模块
- 新 loss
- 解冻 backbone
- 改 decoder 主体

## 评测对象

- `T0 = B0-frozen`
- `T1 = Adapter-only`
- `T2 = HSF-only`
- `T3 = Adapter + HSF`

使用 checkpoint：

- `external/IMIS-Bench/work_dir/phase2_2_trainable_bridge/T1_adapter_only/IMIS_latest.pth`
- `external/IMIS-Bench/work_dir/phase2_2_trainable_bridge/T2_hsf_only/IMIS_latest.pth`
- `external/IMIS-Bench/work_dir/phase2_2_trainable_bridge/T3_adapter_hsf/IMIS_latest.pth`

结果文件：

- `results/phase2_3_full14_bridge_eval/LATEST_phase2_b_minimal.json`
- `results/phase2_3_full14_bridge_eval/LATEST_phase2_b_minimal.csv`
- `results/phase2_3_full14_bridge_eval/LATEST_phase2_b_minimal.md`

## 主结果

| Run | Dice@3 | Dice@5 | Dice@8 | NoC@90 | Avg Interaction Latency (s) | Peak Memory (MB) |
|---|---:|---:|---:|---:|---:|---:|
| T0 | `0.8627` | `0.8794` | `0.8890` | `5.143` | `0.1224` | `3513.5` |
| T1 | `0.8656` | `0.8813` | `0.8965` | `5.071` | `0.1146` | `3621.6` |
| T2 | `0.8683` | `0.8906` | `0.8900` | `4.786` | `0.1164` | `3729.4` |
| T3 | `0.8539` | `0.8663` | `0.8874` | `5.929` | `0.1168` | `3734.9` |

## Delta vs T0

| Run | Delta Dice@5 | Delta Dice@8 | Delta NoC@90 |
|---|---:|---:|---:|
| T1 | `+0.0019` | `+0.0075` | `-0.071` |
| T2 | `+0.0112` | `+0.0009` | `-0.357` |
| T3 | `-0.0130` | `-0.0016` | `+0.786` |

解释：

- `T1`：
  - weak positive
- `T2`：
  - clearest positive signal
- `T3`：
  - 当前 fixed-budget 下没有站住

## Win Rate vs T0

### Dice@5

| Run | Wins | Losses | Ties |
|---|---:|---:|---:|
| T1 | `3` | `11` | `0` |
| T2 | `8` | `6` | `0` |
| T3 | `4` | `10` | `0` |

### Dice@8

| Run | Wins | Losses | Ties |
|---|---:|---:|---:|
| T1 | `7` | `7` | `0` |
| T2 | `8` | `6` | `0` |
| T3 | `8` | `6` | `0` |

## Go / No-Go 判断

### 通过的条件

- 条件 1：
  - 至少一个方法在 `Dice@5` 上超过 `T0`
  - 结论：通过，`T1 / T2`
- 条件 2：
  - 至少一个方法在 `NoC@90` 上优于 `T0`
  - 结论：通过，`T1 / T2`
- 条件 4：
  - Win Rate 明显偏正
  - 结论：`T2` 在 `Dice@5 / Dice@8` 上都是 `8:6`
- 条件 5：
  - 成本不过线
  - 结论：通过
  - latency 没有变差
  - memory 仅小幅上升

### 未通过的条件

- 条件 3：
  - `T3` 不弱于 `T1 / T2`
  - 结论：未通过
  - 当前组合桥 `T3` 明显弱于 `T2`

## 当前结论

### 结论 1

`B` 线没有被否掉。

因为：

- bridge wiring 已干净
- bridge learnability 已成立
- full-14 fixed-budget 下，`T2` 仍能在 `Dice@5` 和 `NoC@90` 上稳定优于 `T0`

### 结论 2

当前正向证据主要来自 `HSF-only`，不是 `Adapter + HSF` 组合。

也就是：

- `T2` 目前是最可信的 bridge 增量
- `T1` 是弱正向
- `T3` 当前 fixed-budget 下没有形成互补，反而退化

### 结论 3

因此当前能支持的不是：

> Local Adapter + HSF 组合已经成立

而更接近：

> Freeze-A2 的 bridge-only 路线仍值得继续，其中 HSF 分支已经在 full-14 上给出最清晰的正向信号。

## 下一步

仍然不要横向扩。

如果继续，只能沿当前线收紧：

1. 不做 `B4`
2. 不做多 seed
3. 不做 small-target / boundary
4. 不解冻 backbone
5. 只在 bridge-only 设定下继续

最合理的后续问题是：

> 为什么 `T2` 过了，而 `T3` 没过？

但这已经是下一阶段问题，不属于当前 Phase 2.3。
