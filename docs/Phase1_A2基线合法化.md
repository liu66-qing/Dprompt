# Phase 1：A2 基线合法化

## 目标

把 `claim_driven实验路径.md` 里的 A0 / A1 / A2 从口头约定变成可执行定义，并在本机 sample BTCV 上先完成一版 legalization。

## 本地操作化定义

### A0：Repo default

- 含义：
  - 尽量贴近公开 `test.py` 的默认推理入口
- 当前本地定义：
  - `prompt_mode=points`
  - `inter_num=1`
  - `image_size=1024`
  - checkpoint 使用公开发布的 `IMISNet-B.pth`

### A1：Paper-aligned

- 含义：
  - 用论文对齐的连续交互协议，把 IMIS-Net 的公开 checkpoint 在本地 sample 上统一重测
- 当前本地定义：
  - `prompt_mode in {points, bboxes}`
  - `inter_num in {1, 3, 5, 8}`
  - `image_size=1024`
- 产出：
  - points / bboxes
  - 1 / 3 / 5 / 8 轮交互 Dice
  - latency
  - peak memory

### A2：Paper-aligned-strong

- 含义：
  - 从 A1 的合法 sweep 中冻结后续唯一主对照面
- 当前本地冻结规则：
  - 下游方法主比较统一使用 `points + K=8`
  - `bboxes + K=8` 保留为 supporting upper-bound，不作为 Phase 2 的 M0 锚点

## 为什么当前 Phase 1 先做“评测协议合法化”

当前机器上已拿到的是：

- 公开 `IMISNet-B.pth`
- 仓库内 sample `BTCV`

当前还没有：

- 完整 IMed-361M 训练数据
- 论文全文中完整可复原的训练 recipe
- 可直接重训并公平比较的 full benchmark 预算

因此本地 Phase 1 先做两件事：

1. 把“repo 默认入口”和“paper-aligned continuous interaction protocol”明确区分
2. 先冻结一个后续 M0 可直接复用的强基线入口

这一步是合法化，不是假装已经完成 full paper reproduction。

## 执行入口

- 配置：
  - `configs/phase1_baselines.yaml`
- 脚本：
  - `scripts/phase1_baseline_eval.py`

推荐命令：

```bash
/root/autodl-tmp/jiujiu/Dprompt/envs/imisbench/bin/python scripts/phase1_baseline_eval.py
```

## 冻结声明

在当前本地 sample legalization 范围内：

- A0 = repo default points K=1
- A1 = points / bboxes 的 1/3/5/8 continuous interaction sweep
- A2 = `points K=8`

后续 Phase 2 的 `M0` 默认直接使用 A2。

## 当前 sample legalization 结果

本次运行输出位于：

- `results/phase1_baselines/LATEST_phase1_baselines.csv`
- `results/phase1_baselines/LATEST_phase1_baselines.md`

关键结果如下：

| Baseline | Prompt | K | Avg Dice | Avg IoU | Avg Sample Latency (s) | Peak Memory (MB) |
|---|---:|---:|---:|---:|---:|---:|
| A0 | points | 1 | 0.8314 | 0.7493 | 0.2103 | 3649.3 |
| A1 | points | 3 | 0.8735 | 0.8028 | 0.3997 | 4449.2 |
| A1 | points | 5 | 0.8913 | 0.8241 | 0.5953 | 4452.1 |
| A1 | points | 8 | 0.8885 | 0.8223 | 0.9015 | 4451.8 |
| A1 | bboxes | 1 | 0.8970 | 0.8286 | 0.1565 | 4546.3 |
| A1 | bboxes | 3 | 0.9060 | 0.8397 | 0.3765 | 4455.8 |
| A1 | bboxes | 5 | 0.9195 | 0.8570 | 0.5924 | 4455.8 |
| A1 | bboxes | 8 | 0.9124 | 0.8482 | 0.9044 | 4458.4 |
| A2 | points | 8 | 0.8885 | 0.8223 | 0.9015 | 4451.8 |

## 当前结论

- A2 已明显强于 A0：
  - `points K=1` 的 `0.8314` 提升到 `points K=8` 的 `0.8885`
- points 分支存在清晰的连续交互增益：
  - `K=1 -> K=3 -> K=5` 持续提升
- 在当前 sample 上，`K=8` 相比 `K=5` 出现轻微回落：
  - 这更像局部饱和或后期修正噪声，不改变 `K=8` 作为 paper-aligned horizon 的冻结逻辑
- bbox 分支整体高于 points 分支：
  - 因此保留为 supporting upper-bound
  - 但 downstream B0 仍冻结在 point 分支，保持与后续 ViT-based enhancement 实验的交互形态一致

## 当前冻结决定

- A2 继续冻结为：
  - `points + K=8 + released IMISNet-B checkpoint`
- Phase 2 的 `B0` 默认直接继承这个入口
