# AGENTS

## 开始前先读
1. `memory/STAGE_MEMORY.md`
2. `claim_driven实验路径.md`
3. `refine-logs/EXPERIMENT_PLAN.md`
4. `refine-logs/EXPERIMENT_TRACKER.md`
5. `docs/实验启动记录.md`
6. `docs/变更记录.md`

## 当前项目目标
- 当前仓库的角色是“实验规范与复现编排层”，不是 IMIS-Bench 主代码仓库。
- 当前主线必须遵守 claim-driven 路线，不要跳阶段：
  1. Phase 0: 跑通 IMIS-Bench 与最小日志链路
  2. Phase 1: A0 / A1 / A2 baseline legalization
  3. Phase 2: B0 / B1 / B2 / B3 minimal enhancement runs
  4. Phase 3: focused ablation 与 local diagnosis
  5. Phase 4: seeds 与 efficiency defense

## 本地规范
- 真实路径只能放在 `configs/paths.local.yaml`，不要硬编码到源码。
- 任何会占用 GPU 的训练或测试，启动前先更新 `docs/实验启动记录.md`。
- 每完成一个阶段或子阶段，都要同时更新：
  - `memory/STAGE_MEMORY.md`
  - `docs/变更记录.md`
- 不要提交数据、环境、checkpoint、日志、输出目录和 `external/` 内容。

## 已接入的本地工作流
- IMIS-Bench 本地根目录：`external/IMIS-Bench`
- ARIS 本地根目录：`external/Auto-claude-code-research-in-sleep`
- Codex 全局 skills 已安装到：`~/.codex/skills`
- 项目级 ARIS skills 入口约定为：`.agents/skills/`
- ARIS/Codex 接入说明见：`docs/ARIS_Codex_接入说明.md`

## 推荐优先调用的 ARIS 技能
- `experiment-plan`: 新主线变更时先把 claim、最小矩阵、run order 和 go/no-go 写清楚
- `experiment-bridge`: 从当前实验规划落到代码与运行桥接
- `run-experiment`: 启动训练或评测任务
- `monitor-experiment`: 查看运行中任务状态
- `analyze-results`: 汇总结果并形成可对比结论
- `result-to-claim`: 判断现有结果究竟支持哪条 claim

## 当前已知限制
- reviewer MCP 还没有正式启用，因为本机没有可用的 `claude` / `gemini` CLI，也没有外部 API 凭证。
- 如后续补齐凭证，运行 `bash scripts/setup_aris_mcp.sh` 即可按条件注册可用 MCP。
