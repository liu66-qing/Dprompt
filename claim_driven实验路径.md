# 一、当前只保留三条 Claim

## Claim 1：Baseline legalization

**所有后续比较都只允许建立在 paper-aligned strong baseline `A2` 上。**

这条不是创新点，是唯一合法参照面。

---

## Claim 2：唯一主命题

**在强 `A2` 基线上，只引入 `HSF-only` 的轻量 trainable bridge，就能在不重写交互流程的前提下，稳定提升 ViT-based IMIS 的交互分割质量与修正效率。**

这就是当前唯一主方法叙事。
不再证明：

- `Adapter + HSF` 必须同时成立
- `T3` 组合一定有互补性
- prompt-aware weighting 是必要组件

---

## Claim 3：效率与范围 defense

**`T2` 的收益不是靠破坏基线或明显增加时延换来的。**

当前只证明两件事：

- bridge wiring 干净，不污染 `A2`
- `T2` 的 latency 不升，memory 只小幅增加

---

# 二、当前主方法定义

## 主方法

**`T2 = A2 + HSF-only`**

工程定义：

- 冻结 `A2`
- 不改交互协议
- 不解冻 backbone
- 只训练 `HSF` 相关 bridge 参数
- 当前 `hsf_blocks = [9, 10, 11]`

## 当前唯一对照

- `T0 = B0-frozen = A2`

## 已封存分支

- `T1 = Adapter-only`
  - 只保留为历史 learnability / ablation 参考
- `T3 = Adapter + HSF`
  - 当前 fixed-budget 下未形成互补
  - **正式封存，不再继续 rescue**
- `B4 / prompt-aware weighting`
  - 当前不进入活动主线

---

# 三、已完成证据链

## Phase 0 / 1：地基已完成

- IMIS-Bench 环境、BTCV sample、checkpoint 已打通
- `A2 = points, K=8` 已冻结为唯一强基线

## Phase 2.1：Zero-perturbation wiring 已完成

- `B0 / B1 / B2 / B3` 的最小实现都能正常前向
- `B0` 与 `A2` 指标一致，说明新增路径未污染基线

## Phase 2.2：Bridge learnability 已完成

- `freeze-A2`
- `disable_text_prompt = true`
- `skip_interaction_training = true`
- `HSF` 已确认可学
- `Adapter` 通过修复初始化后也确认可学

## Phase 2.3：Fixed-Budget Full-14 已完成

核心结果：

- `T0`：
  - `Dice@5 = 0.8794`
  - `Dice@8 = 0.8890`
  - `NoC@90 = 5.143`
- `T2`：
  - `Dice@5 = 0.8906`
  - `Dice@8 = 0.8900`
  - `NoC@90 = 4.786`

阶段结论：

- `T2` 是最清晰的正向 bridge 信号
- `T3` 不成立，不能再做主方法

## Phase 2.4：T2 Confirmation Run 已完成

固定条件：

- seeds = `42 / 43 / 44`
- freeze-A2
- fixed budget：`1 epoch + 2 steps/epoch`
- full `14` test items

### 3-seed 汇总

| System | Dice@5 | Dice@8 | NoC@90 | Latency (s) | Memory (MB) |
|---|---:|---:|---:|---:|---:|
| T0 | `0.8768 +- 0.0077` | `0.8884 +- 0.0029` | `5.333 +- 0.330` | `0.1253 +- 0.0024` | `3540.2 +- 23.1` |
| T2 | `0.8866 +- 0.0042` | `0.8884 +- 0.0062` | `5.190 +- 0.393` | `0.1192 +- 0.0010` | `3752.1 +- 20.1` |

### Delta `T2 - T0`

- `Dice@5 = +0.0098 +- 0.0062`
- `Dice@8 = +0.0000 +- 0.0040`
- `NoC@90 = -0.143 +- 0.214`
- latency：
  - 更快，约 `-4.9%`
- memory：
  - 小幅上升，约 `+6.0%`

### Case-level pooled win rate

- `Dice@5`：
  - `23 win / 17 loss / 2 tie`
- `Dice@8`：
  - `26 win / 16 loss / 0 tie`

### 当前结论

- `Dice@5` 三个 seed 全部翻正
- `NoC@90` 平均更好，且 `3` 个 seed 里有 `2` 个更好
- latency 没变差
- memory 只小幅上升

**因此：`T2` 通过最小确认实验，正式升格为当前唯一主方法。**

## Phase 2.5：T2-only Diagnosis and Defense 已完成

固定动作：

- 只看 `T0 vs T2`
- 不加新模块
- 不恢复 `T3`
- 不重跑主实验

### Efficiency defense

- `Dice@5 = +0.0098 +- 0.0062`
- `Dice@8 = +0.0000 +- 0.0040`
- `NoC@90 = -0.143 +- 0.214`
- Avg Interaction Latency：
  - `-0.0061 +- 0.0014 s`
- wall-clock per case：
  - `-0.0486 +- 0.0110 s`
- Peak Memory：
  - `+211.9 +- 6.8 MB`

这说明：

- `T2` 不是靠更慢的交互换结果
- 当前代价主要是小幅显存增加

### Local diagnosis

当前采用 target-level 诊断，因为 BTCV 的每个 case 含多个结构，这样更适合隔离尺寸和边界因素。

#### Size strata

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

这说明：

- 小目标不是“全面抬升”
- 更像是：
  - 一部分困难小目标有明显收益
  - 但不是所有 small targets 都会提升

#### Boundary complexity strata

- `simple`：
  - `Mean Delta Dice@5 = +0.0030`
  - `Median Delta Dice@5 = -0.0002`
  - `Win Rate = 44.2%`
- `complex`：
  - `Mean Delta Dice@5 = +0.0190`
  - `Median Delta Dice@5 = +0.0006`
  - `Win Rate = 59.5%`

这说明：

- **当前最干净、最可 defend 的增益来源是 complex boundary objects**
- 这条证据比 blanket small-target story 更强

### Representative cases

当前已固定 `4` 类例子，并生成定性图：

- small-target win
- complex-boundary win
- near tie
- failure case

图文件：

- `figures/phase2_5_t2_representative_cases.pdf`
- `figures/phase2_5_t2_representative_cases.png`

### 当前结论

**Phase 2.5 已把主线从“`T2` 只是平均更好”推进到“`T2` 的收益主要集中在 boundary complexity 更高的结构上，而且成本可 defend”。**

---

# 四、当前 Result-to-Claim 判定

> 本轮按 `result-to-claim` 口径做本地判断，未额外起 reviewer 子代理。

## 对旧主张的判定

- 旧主张：
  - `Adapter + HSF` 组合作为主方法成立
- 结论：
  - **不支持**

## 对当前缩窄主张的判定

- 当前主张：
  - `HSF-only` 在强 `A2` 基线上是当前唯一稳定的增量方法候选
- 结论：
  - **支持当前项目推进**
  - 但对论文级泛化主张仍只算 **partial support**

当前能诚实写出的范围是：

> 在当前 BTCV sample、freeze-A2、fixed-budget、full-14 的设定下，`T2 = HSF-only` 已表现出稳定且可重复的正向信号。

当前还不能写的是：

- 一般性地宣称 “分层语义融合在所有 IMIS 条件下都成立”
- 把 `T3` 说成互补组合
- 把 prompt-aware weighting 重新拉回主线

---

# 五、当前 Stop List

下面这些现在都不再做：

- 不做 `T3` rescue
- 不做 `G1 / G2 / G3`
- 不做 adapter 范围缩放
- 不做 staged training
- 不做新 loss
- 不做 `B4`
- 不做新的 trigger / contract 线
- 不做 backbone 解冻

一句话：

> 现在只问 `T2` 还能不能被更扎实地解释和防守，不再问怎么让 `T3` 成立。

---

# 六、下一步只保留一个入口

## 下一阶段

**Phase 3：Paper-ready claim freeze**

## 下一步唯一合理任务

不再开新方法实验，只做：

- 主表定稿
- diagnosis table / figure 整理
- representative cases 写进正文或 appendix
- claim wording freeze

如果后续再开实验，也必须满足：

- 不新增模块
- 不更换方法核
- 不恢复 `T3`
- 不横向扩表

---

# 七、当前一句话总括

**主方法已经从“B3 组合增强”正式收缩为“`T2 = HSF-only`”。**

现在最重要的不是继续找新方法，而是把 `T2` 的 complex-boundary 优势、效率代价和失败案例一起讲清楚。
