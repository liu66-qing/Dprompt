# Phase 2.2：Trainable Bridge

## 目标

只回答一个更小的问题：

> 在完全冻结 A2 主干的前提下，后段局部 adapter 和分层语义融合，能否作为一个可学习的增量桥接层产生非零、非破坏性的正向信号？

## 当前定义

### T0

- `B0-frozen`
- `A2` 直接评测
- 不训练

### T1

- Adapter-only
- 冻结 `A2`
- 只训练 `image_encoder.local_adapters.*`

### T2

- HSF-only
- 冻结 `A2`
- 只训练：
  - `image_encoder.hierarchical_necks.*`
  - `hsf_module.level_weights`

### T3

- Adapter + HSF
- 冻结 `A2`
- 同时训练 T1 和 T2 的 bridge 参数

## 当前实现

### 冻结边界

已在 `external/IMIS-Bench/model.py` 中加入：

- `set_trainable_scope("none" | "adapter_only" | "hsf_only" | "bridge_only")`
- `summarize_trainable_parameters()`

当前审计结果：

| Run | Scope | Trainable Params |
|---|---|---:|
| T0 | `none` | `0` |
| T1 | `adapter_only` | `1,790,208` |
| T2 | `hsf_only` | `17,703,939` |
| T3 | `bridge_only` | `19,494,147` |

对应输出：

- `results/phase2_2_bridge_audit/LATEST_phase2_2_bridge_audit.json`
- `results/phase2_2_bridge_audit/LATEST_phase2_2_bridge_audit.csv`
- `results/phase2_2_bridge_audit/LATEST_phase2_2_bridge_audit.md`

### 训练入口

已在 `external/IMIS-Bench/train.py` 中加入最小 bridge-only 训练开关：

- `--trainable_scope`
- `--local_adapter_blocks`
- `--hsf_blocks`
- `--disable_text_prompt`
- `--skip_interaction_training`
- `--max_steps_per_epoch`

其中：

- `--disable_text_prompt`
  - 避免离线环境下 tokenizer 外网依赖
- `--skip_interaction_training`
  - 因为 bridge-only 训练时，原始 interaction 分支使用 detached image embedding，不再适合作为最小 learnability gate

### 评测入口

已新增：

- `configs/phase2_2_bridge_eval.yaml`

并让 `scripts/phase2_b_minimal_eval.py` 支持：

- method-specific checkpoint
- 从训练态 wrapper checkpoint 中回填整模型权重

## 结构性发现

### 1. HSF 分支本来就是可学习的

短训后：

- `T2 hsf_module.level_weights`
  - `[4.85e-06, 3.87e-06, 3.03e-06]`
- `T3 hsf_module.level_weights`
  - `[-1.66e-05, -1.79e-05, -1.06e-05]`

说明：

- HSF 的 zero-gated 设计没有堵死梯度
- 桥接层可以在冻结 A2 主干下学出非零增量

### 2. 原始 Local Adapter 初始化会堵死梯度

最初实现是：

- depthwise = `0`
- pointwise = `0`

这会导致：

- 初始输出为 `0`
- 但 `T1/T3` 的 adapter 梯度也被一起堵死

### 3. 已做最小修复

当前 adapter 初始化改为：

- depthwise = identity-like 3x3
- pointwise = `0`

因此：

- 初始输出仍然为 `0`
- 不污染 `B0`
- 但 pointwise 分支可以立刻接到非零梯度

修复后短训结果：

- `T1 adapter_norm = 83.17`
- `T3 adapter_norm = 83.18`

说明：

- adapter 分支已从“死桥”变成“可学习桥”

## 最小 smoke 结果

设置：

- 训练：`1 epoch x 2 steps`
- 评测：`2` 个 test case
- 目的：只验证“能学”与“不会炸”

结果：

| Run | Dice@5 | Dice@8 | NoC@90 |
|---|---:|---:|---:|
| T0 | `0.8330` | `0.8515` | `9.0` |
| T1 | `0.8562` | `0.8804` | `6.0` |
| T2 | `0.8664` | `0.8789` | `8.0` |
| T3 | `0.8582` | `0.8890` | `6.5` |

当前只把它解释为：

- bridge-only 训练已经能产生非零、非破坏性的早期正向信号

当前不把它解释为：

- 主文结果
- 多 seed 结论
- full-sample 稳定优势

## 当前结论

Phase 2.2 的问题已经得到初步回答：

> 在冻结 A2 主干下，HSF 分支本身可学习；修复初始化后，Local Adapter 分支也可学习；组合桥接层已能在最小 smoke 中产生非零且不崩的正向信号。

## 下一步

不要横向扩表。

下一步应继续保持克制，只做一个更小的放大验证：

1. 维持 bridge-only 冻结策略不变
2. 将 `2-step smoke` 放大到一个固定小预算 run
3. 优先跑：
   - `T1`
   - `T2`
   - `T3`
4. 在 full `14` 个 test item 上复核：
   - Dice@5
   - Dice@8
   - NoC@90
   - bridge 参数是否持续远离初始化
