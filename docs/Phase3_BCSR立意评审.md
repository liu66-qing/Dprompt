# Phase 3 立意评审：Boundary-Conditioned Semantic Routing

## 评审问题

当前这版新立意是否已经足够开启下一阶段工作？

候选中心命题是：

> 在强 ViT-based promptable interactive segmentation 中，剩余误差并非均匀分布，而是在结构歧义区域表现为层级语义失配；最终层高语义足以确定对象整体，却不足以在复杂边界、细薄结构和邻近组织交界处提供稳定局部判别。

对应主方法候选：

- `Boundary-Conditioned Semantic Routing`

对应副方法候选：

- `Boundary-Band Consistency Supervision`

## 结论

### 可以开启

**可以开启这部分工作。**

但必须按下面这个更严格的状态来开启：

- `Boundary-Conditioned Semantic Routing`
  - 可以作为 **下一阶段唯一主方法假设**
- `Boundary-Band Consistency Supervision`
  - 目前只能作为 **可选训练稳定器候选**
  - 不能在今天就冻结成并列副创新

换句话说：

> 现在可以开启 `BCSR` 这条线，但不能把“routing + boundary-band supervision”整套一起提前当成已经成立的最终方法。

## 为什么可以开启

### 当前证据已经支持的问题选择

从已完成的 Phase 2.3 / 2.4 / 2.5 看，当前最硬的证据链是：

- `T2 = HSF-only` 有稳定正向信号
- 增益最干净地集中在 `complex boundary` objects
- 效率代价可 defend

这至少支持下面这句话：

> 固定的分层语义融合已经有价值，而剩余收益更集中出现在结构歧义更强的区域。

因此把问题从“固定 HSF 是否有用”升级成“在歧义区域应如何选择更合适的语义层级”，是自然延伸，不是凭空换题。

### 当前叙事比单纯“复杂边界更难”更强

如果只说：

> 复杂边界是瓶颈

这还是偏现象层。

你现在这版把它提升成：

> 复杂边界是结构歧义区域的可观测表现，而真正问题是层级语义失配。

这个机制层表述更接近 reviewer 会认真对待的问题定义。

### 当前升级仍然是最小必要升级

你不是在：

- 回到 `T3`
- 再加一个新 backbone
- 重做 decoder
- 堆一堆 boundary 分支

而是在：

- 以 `T2 = HSF-only` 为起点
- 只把“固定融合”升级成“条件路由”

这仍然属于一条节制的、从现有证据长出来的升级路线。

## 为什么不能直接把它写成已证实主张

### 当前证据支持的是“问题可以立”，不是“机制已经证实”

当前数据支持：

- 多层语义有用
- complex boundary 更受益

但当前数据还**不直接支持**：

- “最终层一定发生了层级语义失配”
- “动态路由一定比固定 HSF 更优”
- “边界带一致性监督一定必要”

所以这里必须分清：

- **可开启的研究方向**
- **已被现有实验支持的论文 claim**

现在你拿到的是前者，不是后者。

### `Boundary-Band Consistency Supervision` 还不该今天就写死

这个组件是合理的，而且很可能有用。

但就当前阶段来说，它更应该被定义成：

> routing 学稳时的训练稳定器候选

而不是：

> 已冻结的第二创新点

否则一开始就会把方法重新写重。

## 我给出的正式判定

### 对当前新中心命题

- Verdict:
  - `can_start = yes`
  - `claim_supported_now = partial`

更准确地说：

- 作为 **Phase 3 的研究假设**：
  - 可以启动
- 作为 **当前论文已成立中心命题**：
  - 还不行

### 对主创新点

- `Boundary-Conditioned Semantic Routing`
  - 可以冻结为下一阶段唯一主方法候选

### 对副创新点

- `Boundary-Band Consistency Supervision`
  - 先降级成 optional stabilizer
  - 只有在 routing-only 已经可学、但不稳时，再正式抬升

## 当前最安全的冻结版本

### 已归档、已被支持的结论

> `T2 = HSF-only` 在当前 BTCV sample、freeze-A2、fixed-budget 设定下是可 defend 的轻量 bridge；其收益最清晰地集中在 boundary complexity 更高的结构上。

### 新开启、但仍属假设的中心命题

> 强 ViT-based promptable interactive segmentation 的剩余误差在结构歧义区域表现为层级语义失配；复杂边界是这种失配的可观测表现。

### 新开启的唯一主方法候选

> `Boundary-Conditioned Semantic Routing`

### 新开启的可选训练稳定器

> `Boundary-Band Consistency Supervision`

## 下一步最小工作包

如果启动 Phase 3，我建议只允许这三个动作：

1. `Routing-only` 方法定义冻结
2. `Routing-only` 的 zero-perturbation / learnability gate
3. 只有当 `routing-only` 已出现正向信号但训练不稳时，再加 `Boundary-Band Consistency Supervision`

明确不做：

- 不把 supervision 和 routing 一起捆成首轮大系统
- 不恢复 `T3`
- 不加新 decoder 大分支
- 不开新的横向模块搜索

## 一句话结论

**这条线可以开，但要以“`BCSR` 是新假设驱动的下一阶段主方法候选”来开启，而不是把它写成已经被 `T2` 结果证明的最终论文主张。**
