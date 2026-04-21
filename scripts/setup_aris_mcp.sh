#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARIS_REPO="$PROJECT_ROOT/external/Auto-claude-code-research-in-sleep"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
TARGET_ROOT="$CODEX_HOME/mcp-servers"

if [[ ! -d "$ARIS_REPO/mcp-servers" ]]; then
  echo "error: ARIS mcp-servers 目录不存在: $ARIS_REPO/mcp-servers" >&2
  exit 1
fi

mkdir -p "$TARGET_ROOT"

copy_server_dir() {
  local name="$1"
  local src="$ARIS_REPO/mcp-servers/$name"
  local dst="$TARGET_ROOT/$name"
  if [[ ! -d "$src" ]]; then
    echo "skip: missing source dir $src"
    return 1
  fi
  mkdir -p "$dst"
  cp -a "$src"/. "$dst"/
  echo "synced: $name -> $dst"
}

mcp_exists() {
  codex mcp get "$1" >/dev/null 2>&1
}

reset_mcp() {
  local name="$1"
  if mcp_exists "$name"; then
    codex mcp remove "$name" >/dev/null
    echo "removed existing MCP config: $name"
  fi
}

require_python_module() {
  python3 - <<'PY' "$1" >/dev/null 2>&1
import importlib, sys
sys.exit(0 if importlib.util.find_spec(sys.argv[1]) else 1)
PY
}

register_llm_chat() {
  local api_key="${LLM_API_KEY:-${OPENAI_API_KEY:-}}"
  local base_url="${LLM_BASE_URL:-${OPENAI_BASE_URL:-https://api.openai.com/v1}}"
  local model="${LLM_MODEL:-gpt-4o}"
  local server_py="$TARGET_ROOT/llm-chat/server.py"

  copy_server_dir "llm-chat" >/dev/null || return 0

  if [[ -z "$api_key" ]]; then
    echo "skip: llm-chat needs LLM_API_KEY or OPENAI_API_KEY"
    return 0
  fi
  if ! require_python_module "httpx"; then
    echo "skip: llm-chat needs python3 module httpx"
    return 0
  fi

  reset_mcp "llm-chat"
  codex mcp add llm-chat \
    --env "LLM_API_KEY=$api_key" \
    --env "LLM_BASE_URL=$base_url" \
    --env "LLM_MODEL=$model" \
    -- python3 "$server_py"
  echo "registered: llm-chat"
}

register_minimax_chat() {
  local api_key="${MINIMAX_API_KEY:-}"
  local base_url="${MINIMAX_BASE_URL:-https://api.minimax.io/v1}"
  local model="${MINIMAX_MODEL:-MiniMax-M2.7}"
  local server_py="$TARGET_ROOT/minimax-chat/server.py"

  copy_server_dir "minimax-chat" >/dev/null || return 0

  if [[ -z "$api_key" ]]; then
    echo "skip: minimax-chat needs MINIMAX_API_KEY"
    return 0
  fi
  if ! require_python_module "httpx"; then
    echo "skip: minimax-chat needs python3 module httpx"
    return 0
  fi

  reset_mcp "minimax-chat"
  codex mcp add minimax-chat \
    --env "MINIMAX_API_KEY=$api_key" \
    --env "MINIMAX_BASE_URL=$base_url" \
    --env "MINIMAX_MODEL=$model" \
    -- python3 "$server_py"
  echo "registered: minimax-chat"
}

register_claude_review() {
  local server_py="$TARGET_ROOT/claude-review/server.py"
  copy_server_dir "claude-review" >/dev/null || return 0

  if ! command -v claude >/dev/null 2>&1; then
    echo "skip: claude-review needs local 'claude' CLI"
    return 0
  fi

  reset_mcp "claude-review"
  codex mcp add claude-review -- python3 "$server_py"
  echo "registered: claude-review"
}

register_gemini_review() {
  local server_py="$TARGET_ROOT/gemini-review/server.py"
  copy_server_dir "gemini-review" >/dev/null || return 0

  if ! command -v gemini >/dev/null 2>&1; then
    echo "skip: gemini-review needs local 'gemini' CLI"
    return 0
  fi

  reset_mcp "gemini-review"
  codex mcp add gemini-review -- python3 "$server_py"
  echo "registered: gemini-review"
}

register_feishu_bridge() {
  local server_py="$TARGET_ROOT/feishu-bridge/server.py"
  copy_server_dir "feishu-bridge" >/dev/null || return 0

  if [[ -z "${FEISHU_APP_ID:-}" || -z "${FEISHU_APP_SECRET:-}" ]]; then
    echo "skip: feishu-bridge needs FEISHU_APP_ID and FEISHU_APP_SECRET"
    return 0
  fi
  if ! require_python_module "lark_oapi"; then
    echo "skip: feishu-bridge needs python3 module lark_oapi"
    return 0
  fi

  reset_mcp "feishu-bridge"
  codex mcp add feishu-bridge \
    --env "FEISHU_APP_ID=${FEISHU_APP_ID:-}" \
    --env "FEISHU_APP_SECRET=${FEISHU_APP_SECRET:-}" \
    --env "FEISHU_USER_ID=${FEISHU_USER_ID:-}" \
    -- python3 "$server_py"
  echo "registered: feishu-bridge"
}

register_llm_chat
register_minimax_chat
register_claude_review
register_gemini_review
register_feishu_bridge

echo
echo "Current MCP list:"
codex mcp list || true
