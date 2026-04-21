# Phase 2.5：T2-only Diagnosis and Defense

## 目标

只回答三件事：

1. `T2` 为什么更好
2. `T2` 在哪些局部场景更好
3. `T2` 的收益是否值得它的成本

## 固定前提

- 只保留：
  - `T0 = A2 / B0-frozen`
  - `T2 = HSF-only`
- 不新增模块
- 不恢复 `T3`
- 不改训练 recipe
- 不重跑主实验

输入结果：

- `results/phase2_4_t2_confirmation/summary/LATEST_phase2_4_t2_confirmation_summary.json`
- `results/phase2_4_t2_confirmation/seed_*/LATEST_phase2_b_minimal.json`

输出结果：

- `results/phase2_5_t2_diagnosis/LATEST_phase2_5_t2_diagnosis.md`
- `results/phase2_5_t2_diagnosis/LATEST_phase2_5_t2_diagnosis.json`
- `figures/phase2_5_t2_performance_cost.pdf`
- `figures/phase2_5_t2_representative_cases.pdf`

## 分析单位

local diagnosis 使用的是：

> `image_root + target_name`

也就是 target-level object。

这样做的原因是：

- BTCV 每个 case 同时包含多个结构
- 如果直接按 case 做尺寸 / 边界分层，会把多个目标混在一起
- target-level 更适合回答 “哪类结构更受益”

## Efficiency Defense

| Method | Dice@5 | Dice@8 | NoC@90 | Avg Interaction Latency (s) | Peak Memory (MB) | Wall-clock / case (s) |
|---|---:|---:|---:|---:|---:|---:|
| T0 | `0.8768 +- 0.0077` | `0.8884 +- 0.0029` | `5.333 +- 0.330` | `0.1253 +- 0.0024` | `3540.2 +- 23.1` | `1.0023 +- 0.0188` |
| T2 | `0.8866 +- 0.0042` | `0.8884 +- 0.0062` | `5.190 +- 0.393` | `0.1192 +- 0.0010` | `3752.1 +- 20.1` | `0.9537 +- 0.0079` |
| Delta `T2 - T0` | `+0.0098 +- 0.0062` | `+0.0000 +- 0.0040` | `-0.143 +- 0.214` | `-0.0061 +- 0.0014` | `+211.9 +- 6.8` | `-0.0486 +- 0.0110` |

### 当前结论

- `T2` 不是靠更慢的交互换结果
- 当前 wall-clock 和 interaction latency 都更好
- 代价主要是：
  - 显存上升约 `+6%`

因此当前 efficiency defense 是成立的。

## Local Diagnosis

### 尺寸分层

尺寸使用 GT area ratio 的三分位数切分：

- `small <= 0.18%`
- `medium = 0.18% ~ 0.83%`
- `large > 0.83%`

| Group | Count | Mean Delta Dice@5 | Median Delta Dice@5 | Delta NoC@90 | Dice@5 Win Rate |
|---|---:|---:|---:|---:|---:|
| small | `29` | `+0.0144` | `-0.0008` | `-0.069` | `37.9%` |
| medium | `28` | `+0.0167` | `+0.0003` | `+0.024` | `57.1%` |
| large | `28` | `+0.0014` | `+0.0009` | `+0.036` | `60.7%` |

解释：

- `small` 的均值是正的
- 但 median 是负的，win rate 也低
- 所以 small-target 只能算 **部分支持**
- 更准确的说法是：
  - `T2` 对一部分困难小目标非常有帮助
  - 但不是 uniform uplift

### 边界复杂度分层

边界复杂度使用：

> `perimeter / sqrt(area)`

并按中位数切成 `simple / complex`。

| Group | Count | Mean Delta Dice@5 | Median Delta Dice@5 | Delta NoC@90 | Dice@5 Win Rate |
|---|---:|---:|---:|---:|---:|
| simple | `43` | `+0.0030` | `-0.0002` | `+0.016` | `44.2%` |
| complex | `42` | `+0.0190` | `+0.0006` | `-0.024` | `59.5%` |

解释：

- `complex boundary` 是当前最干净的正向信号
- 它同时满足：
  - 更大的 mean Delta Dice@5
  - 正的 median Delta Dice@5
  - 更高的 win rate
  - `NoC@90` 方向也更好

### 当前最稳的解释

> `T2 = HSF-only` 的收益更像是对 boundary complexity 更高的结构提供了更稳的后段语义与局部几何支持，而不是对所有 small targets 做统一提升。

## Representative Cases

当前固定 `4` 类 case：

1. small-target win
2. complex-boundary win
3. near tie
4. failure case

对应图：

- `figures/phase2_5_t2_representative_cases.pdf`
- `figures/phase2_5_t2_representative_cases.png`

对应对象：

| Bucket | Image | Target | Delta Dice@5 | 说明 |
|---|---|---:|---:|---|
| small-target win | `ABD_038_74.png` | `adrenal_gland_left` | `+0.3015` | 小目标上有非常明显的 gain |
| complex-boundary win | `ABD_038_54.png` | `liver` | `+0.2880` | 边界复杂结构上 gain 很清晰 |
| near tie | `ABD_037_71.png` | `gallbladder` | `+0.0000` | T0 与 T2 基本持平 |
| failure case | `ABD_038_94.png` | `inferior_vena_cava` | `-0.1167` | 明确展示 T2 也有失败样本 |

## 最终结论

### 已经支持的

- `T2` 是当前唯一稳定主方法
- `T2` 的收益不是靠更慢的交互换来的
- `T2` 的最强定性 / 定量支撑来自：
  - complex boundary objects

### 只部分支持的

- blanket small-target story

### 当前最合适的论文表述

> 在当前 BTCV sample、freeze-A2、fixed-budget 的设定下，`T2 = HSF-only` 提供了稳定且可重复的增量；其收益最清晰地集中在 boundary complexity 更高的结构上，同时保持了可 defend 的效率代价。

## 下一步

不再开新实验。

下一步只做：

- main table / diagnosis table 定稿
- representative figures 入文
- claim wording freeze
