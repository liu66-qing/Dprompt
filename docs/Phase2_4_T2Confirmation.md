# Phase 2.4：T2 Confirmation Run

## 目标

只回答一个问题：

> `T2 = HSF-only` 的正向信号，在固定小预算、full `14` test items、`3` 个 seeds 下，是否稳定到足以正式升格为主方法？

## 固定条件

- `T0 = A2 / B0-frozen`
- `T2 = HSF-only`
- freeze-A2
- `disable_text_prompt = true`
- `skip_interaction_training = true`
- `trainable_scope = hsf_only`
- `hsf_blocks = [9, 10, 11]`
- fixed budget：
  - `1 epoch`
  - `2 steps / epoch`
- seeds：
  - `42`
  - `43`
  - `44`

结果目录：

- `results/phase2_4_t2_confirmation/`
- `results/phase2_4_t2_confirmation/summary/LATEST_phase2_4_t2_confirmation_summary.md`
- `results/phase2_4_t2_confirmation/summary/LATEST_phase2_4_t2_confirmation_summary.json`

## 主结果

| System | Dice@5 | Dice@8 | NoC@90 | Avg Interaction Latency (s) | Peak Memory (MB) |
|---|---:|---:|---:|---:|---:|
| T0 | `0.8768 +- 0.0077` | `0.8884 +- 0.0029` | `5.333 +- 0.330` | `0.1253 +- 0.0024` | `3540.2 +- 23.1` |
| T2 | `0.8866 +- 0.0042` | `0.8884 +- 0.0062` | `5.190 +- 0.393` | `0.1192 +- 0.0010` | `3752.1 +- 20.1` |

## Delta `T2 - T0`

- `Dice@5 = +0.0098 +- 0.0062`
- `Dice@8 = +0.0000 +- 0.0040`
- `NoC@90 = -0.143 +- 0.214`
- latency：
  - 约 `-4.9%`
- memory：
  - 约 `+6.0%`

## Per-seed 结果

| Seed | Delta Dice@5 | Delta Dice@8 | Delta NoC@90 |
|---|---:|---:|---:|
| 42 | `+0.0119` | `+0.0041` | `-0.357` |
| 43 | `+0.0148` | `-0.0001` | `-0.143` |
| 44 | `+0.0028` | `-0.0039` | `+0.071` |

解释：

- `Dice@5` 三个 seed 全部翻正
- `NoC@90` 在 `3` 个 seed 中有 `2` 个更好，均值也更好
- `Dice@8` 基本持平，没有形成新的负担

## Pooled Win Rate vs `T0`

- `Dice@5`：
  - `23 win / 17 loss / 2 tie`
- `Dice@8`：
  - `26 win / 16 loss / 0 tie`

## Result-to-Claim Gate

本轮按 `result-to-claim` 的口径做本地判断，未额外起 reviewer 子代理。

### 对旧主张

- Intended claim:
  - `T3 = Adapter + HSF` 是主方法
- Verdict:
  - `claim_supported = no`

### 对当前缩窄主张

- Intended claim:
  - `T2 = HSF-only` 是当前唯一稳定的主方法候选
- Verdict:
  - `claim_supported = partial`

这里的 `partial` 不是说这轮确认失败，而是说：

- 对项目路由：
  - 已足够支持把主方法正式收缩到 `T2`
- 对论文级泛化主张：
  - 还缺 local diagnosis / paper defense

## 最终决策

### 决策 1

**正式宣布：`T2 = HSF-only` 成为当前唯一主方法。**

### 决策 2

**`T3` 封存。**

含义是：

- 不再 rescue
- 不再做 `G1 / G2 / G3`
- 不再做 adapter 范围缩放
- 不再做 `B4`

### 决策 3

如果继续推进，下一步只允许做：

- `T0 vs T2` 的 small-target / boundary 诊断
- efficiency defense
- 论文叙事收束

## 一句话结论

这轮 Phase 2.4 已经把问题从“`T3` 为什么不行”收束成了“围绕 `T2` 做解释和防守”。
