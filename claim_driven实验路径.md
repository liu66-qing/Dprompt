
# 一、最终论文只证明三条 Claim

## Claim 1：Baseline legalization

**我们先建立 paper-aligned strong IMIS-Net baseline，避免 paper 与公开代码配置漂移造成的比较失真。**

这条不是创新点，是地基。
它的作用只有一个：**锁死后续唯一合法对照基线 A2**。

---

## Claim 2：唯一主命题

**新增 prompt 只有在一个 canonical、full-history-conditioned correction contract 中，才会稳定地转化为交互效率提升；它不能被等价地视为“又一个 local refinement trigger”。**

这条是全文唯一真正的方法主张。
全文所有实验都要服务它。

---

## Claim 3：效率与预算是 defense

**这个 correction contract 在 matched / comparable budget 下仍然提升交互效率，而不是单纯增加计算。**

这条不是头号创新。
它的任务是挡住：

* 你只是更贵
* 你只是 another crop trick
* 你只提升了静态 Dice

---

# 二、主文只保留四根柱子

## 柱子 1：A2 合法化基线

主文只展示三档：

* A0：Repo default
* A1：Paper-aligned
* A2：Paper-aligned-strong

目标不是结果多，而是证明：
**后续所有方法必须只和 A2 比。**

---

## 柱子 2：M0 / M1 / M3 最小 formulation 对比

主文核心只保留：

* **M0**：A2 baseline
* **M1**：simple crop refinement
* **M3**：contract-correction

如果你要保留 M2，只放补表，不让它抢主文叙事。

这组真正证明的是：

* **M1 > M0**：普通 local refinement 的上限
* **M3 > M1**：不是 crop trick，而是 contract 本身有效

---

## 柱子 3：D 组

必须保留：

* D1：delta-only
* D2：full-history
* D3：full-history + delta embedding

这组现在证明的是：

> 新增 prompt 本身不够；
> 只有历史 prompt 一起进入 correction contract，局部修正才是合法的。

这是你最关键的“去 trigger 化”证据。

---

## 柱子 4：C5 Trigger–Budget Sweep

保留，但只证明一件事：

> 这个 contract 在不同预算下如何退化。

它不是证明 trigger 是主创新，
而是证明：**contract 的部署曲线是平滑、可控、可解释的。**

---

# 三、最终方法定义

## 方法名

**M3 = Contract-Correction**

## 一句话定义

对于每次新增 prompt，我们**不直接执行局部 refinement**。
我们先判断它是否意味着一个**局部约束被违反的 correction event**；如果是，就实例化一个 **canonical correction space**，把 ROI 内**全部历史 prompts**重映射进去，并在这个空间里执行局部 correction。

---

## M3 的唯一不可替代因子

**canonical + full-history-conditioned**

这就是方法核。
其他全部降级：

* delta prompt：事件触发源
* trigger：部署机制
* budget：效率约束
* local branch：执行器
* serial/logit fusion：工程实现

---

# 四、完整 Claim-driven 实验路线图

---

## Phase 0：IMIS-Bench 跑通 + 日志模板定型

### 目标

先证明你真的把 IMIS-Bench 跑通，不是在空气里设计方法。

### 要做

* 跑 repo default smoke run
* 固定统一日志格式
* 生成单 case 交互轨迹模板

### 必须记录

* 配置
* seed
* split
* 每轮交互 Dice
* 每轮是否触发 correction
* 每轮 latency
* correction ROI
* 一个完整 case 从第 1 轮到第 (K) 轮的轨迹图

### 产出

* 复现实验卡
* 交互日志模板
* 轨迹图模板

### 预算

* **0.2–0.5 GPU-day**

### Stop / Go

* 跑不通：停止方法开发
* 跑通：进入 Phase 1

---

## Phase 1：A2 基线合法化

### 目标

建立三档合法基线，冻结后续唯一参照面。

### 组别

* A0：Repo default
* A1：Paper-aligned
* A2：Paper-aligned-strong

### 建议 A2 设定

尽量对齐论文主设定：

* 1024 输入
* patch 16
* 连续交互 (K=8)
* decoder output 256×256
* decoder dim = 768

### 指标

* Point Dice
* Bbox Dice
* 1/3/5/8 interaction Dice
* latency
* Peak Memory

### 产出

* A0/A1/A2 基线表
* 一个 clear statement：后续全部只和 A2 比

### 预算

* **1–3 GPU-days**（子集）
* **3–8 GPU-days**（更完整）

### Stop / Go

* 如果 A2 没稳定强于 A0/A1，不做方法
* A2 立住，再进 Phase 2

---

## Phase 2：最小可证 Run（只验证主命题）

### 目标

只回答一个问题：

> 新增 prompt 是否只有在 canonical、full-history-conditioned correction contract 中，才真正带来交互效率提升？

### 比较组

* **M0**：A2
* **M1**：simple crop refinement
* **M3**：contract-correction

### M3 最小实现只保留

1. delta prompt 触发 correction event
2. ROI proposer
3. canonical correction space
4. full-history prompt remapping
5. spacing-preserving local view
6. infer-time selective trigger
7. serial correction + logit-space fusion

### 明确不做

* routing
* RL gate
* fancy acceptor
* adapter
* extra memory tricks
* consistency 套件

### 主指标

* NoC@90
* Correction Gain@3 / @5
* Trigger Rate
* Peak Memory
* per-interaction latency

### 最低通过门槛

#### 任务门槛

* **NoC@90 下降 ≥ 5%**
  或
* **Correction Gain@3 / @5 明显提升**

#### 成本门槛

* Trigger Rate 明显 < 100%
* Peak Memory 不超过 A2 的 **1.2–1.35×**
* 平均交互 latency 不超过 A2 的 **1.3–1.5×**

#### 解释性门槛

* **M3 > M1**：不是 another crop trick
* triggered corrections 的平均收益 > non-triggered pseudo-corrections

### 预算

* **2–4 GPU-days**

### Stop / Go

* 如果 M3 不能稳定赢 M1，不继续
* 如果 M3 赢 M1，但 wall-clock / memory 完全不可控，要先修工程
* 如果 M3 在 NoC 或 Gain 上有明确正向信号，进入 Phase 3

---

# 五、主文必须做的核心消融

---

## D 组：证明“trigger 不是核心，contract 才是核心”

### 组别

* D1：delta-only
* D2：full-history
* D3：full-history + delta embedding

### 目的

证明：

* 不是“新增 prompt 本身”在起作用
* 而是“历史 prompt 共同约束下的 correction contract”在起作用

### 主指标

* NoC@90
* Gain@3 / @5
* prompt contradiction count（有条件就加）
* 失败例子数

---

## C5：Trigger–Budget Sweep

### 横轴

* threshold (\tau)
  或
* budget level：strict / medium / relaxed

### 纵轴

* NoC@90
* Gain
* Trigger Rate
* latency
* Peak Memory
* wall-clock

### 目的

证明：

* contract 在不同预算下是可调、可退化的
* budget-aware 不是口号

---

# 六、主文必须保留的三块可信度建设

---

## 1. 三个 seeds

至少：

* 主表：3 seeds
* D 组：3 seeds

报告：

* mean ± std
  或
* 95% CI

---

## 2. 双 simulator

至少两个：

### Simulator A：理想型

* 贴近论文默认交互规则

### Simulator B：噪声型

* 更大 click 偏移
* 更松 bbox
* 顺序更乱

### 目的

证明：

* 你不是 overfit 某一个 prompt simulator

---

## 3. per-interaction wall-clock

必须报：

* 平均每次交互 latency
* correction 被触发时 latency
* 不触发时 latency
* 达到 NoC@90 的总 wall-clock

### 目的

证明：

* NoC 下降不是拿更慢的人机过程换来的

---

# 七、附录里再放的 defense

主文不要塞太多。
这些全降级到附录：

* B7：serial logit fusion vs feature-level fusion surrogate
* G 组：acceptance / fusion 细节
* E 组更多 canonicalization 变体
* failure cases 详细统计
* 更多轨迹图
* 更多分层分析

---

# 八、最终 Ablation 目录

## 主文 Ablation

* A：Baseline legalization（A0/A1/A2）
* M：M0/M1/M3 minimal formulation comparison
* D：delta-only vs full-history vs delta embedding
* C5：trigger–budget sweep

## 附录 Ablation

* E：canonicalization variants
* F：train-all infer-selectively vs hard-trigger train
* G：acceptance / fusion variants
* B7：serial vs feature-level fusion surrogate

---

# 九、最终预算与执行顺序

## Week 1

### 任务

* Phase 0
* Phase 1

### 输出

* 日志模板
* A0/A1/A2
* 一张 baseline legalization 表

### 预算

* **1–3 GPU-days**

---

## Week 2

### 任务

* Phase 2 MVP
* M0/M1/M3

### 输出

* 最小 go / no-go 结果
* NoC / Gain / Trigger Rate / Memory / latency 表

### 预算

* **2–4 GPU-days**

---

## Week 3

### 任务

* D 组
* C5 sweep
* 3 seeds

### 输出

* 两张主文核心图表：

  * D 组表
  * trigger–budget 曲线

### 预算

* **3–6 GPU-days**

---

## Week 4

### 任务

* 双 simulator
* per-interaction wall-clock
* failure cases 小节
* 附录补充实验

### 输出

* robustness 表
* wall-clock 表
* 失败案例图

### 预算

* **4–8 GPU-days**

---

## 总预算

### 最小可证版

* **4–8 GPU-days**

### 可投稿版

* **10–20 GPU-days**（子集前提）
* 更完整复现会更高

---

# 十、最后一句最终执行原则

> **先证明“canonical, full-history-conditioned correction contract”是必要的，再谈 trigger、预算和部署；绝不反过来。**

也就是说，在下面这些还没成立前，不要扩：

* routing
* 更复杂 acceptor
* adapter
* multi-memory
* 更复杂局部分支

因为你现在最该证明的，不是“我有很多设计”，而是：

> **新增 prompt 只有在 canonical、history-conditioned correction contract 中，才真正转化为交互效率提升。**

这就是整理后的**完整 Claim-driven 实验路线图**。
如果你愿意，我下一步直接给你整理成**论文实验章节目录 + 每张图表标题**。

[1]: https://openaccess.thecvf.com/content/CVPR2025/papers/Cheng_Interactive_Medical_Image_Segmentation_A_Benchmark_Dataset_and_Baseline_CVPR_2025_paper.pdf "Interactive Medical Image Segmentation: A Benchmark Dataset and Baseline"
