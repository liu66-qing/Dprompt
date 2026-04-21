# ARIS + Codex 接入说明

## 当前状态

截至 `2026-04-21`，本项目内 ARIS 接入状态如下：

- ARIS 仓库已同步到 `external/Auto-claude-code-research-in-sleep`
- IMIS-Bench 仓库已同步到 `external/IMIS-Bench`
- Codex 全局 skills 已安装到 `~/.codex/skills`
- reviewer bridge 文件已同步到 `~/.codex/mcp-servers/claude-review` 与 `~/.codex/mcp-servers/gemini-review`
- `codex mcp list` 目前仍为空，因为当前机器没有：
  - 可用的 `claude` CLI
  - 可用的 `gemini` CLI
  - 可用的 `LLM_API_KEY` / `OPENAI_API_KEY` / `MINIMAX_API_KEY`

这意味着：

- skill 可以直接用
- reviewer MCP 不能假装已可用
- 后续补齐凭证后，可用 `bash scripts/setup_aris_mcp.sh` 做条件式注册

## 项目内推荐工作流

围绕 `Dprompt` 当前阶段，优先使用这些 ARIS 技能：

- `experiment-bridge`
  - 用于把 claim-driven 规划落实到“环境搭建、代码可跑、实验可发车”
- `run-experiment`
  - 用于真正启动训练或评测任务
- `monitor-experiment`
  - 用于查看运行进度和日志状态
- `analyze-results`
  - 用于汇总结果并形成对比表或阶段结论
- `result-to-claim`
  - 用于判断结果究竟支持哪条 claim，避免叙事先行

## MCP 启用方式

运行：

```bash
bash scripts/setup_aris_mcp.sh
```

这个脚本会做三件事：

1. 把 ARIS 的 MCP server 文件同步到 `~/.codex/mcp-servers/`
2. 检查本机是否具备可用条件
3. 只注册真正能跑的 MCP，缺条件的会明确跳过

## 当前建议

- 当前先把 ARIS 用作技能和流程规范层
- reviewer MCP 等凭证齐全后再启用
- 所有阶段结果必须回写到：
  - `memory/STAGE_MEMORY.md`
  - `docs/实验启动记录.md`
  - `docs/变更记录.md`
