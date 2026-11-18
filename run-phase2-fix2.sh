#!/bin/bash
# Claude leg — Phase 2 fix round 2 (story generate LLM gagal 502/failed: httpx trust_env gagal parsing no_proxy IPv6 berkurung).
# Mirrors claude/run-phase2-fix.sh (CCR gateway :3456, model ultra-550b).
# Token gateway dibaca dari file, bukan ditulis di sini. JANGAN tulis kunci di sini.
cd "$HOME/workspace/micro-drama-saas/claude" || exit 1
mkdir -p logs
bash "$HOME/infra/start-opencode-stack.sh" >> logs/claude-phase2-fix2.log 2>&1
bash start-ccr.sh >> logs/claude-phase2-fix2.log 2>&1 || { echo "phase2-fix2: CCR start failed"; exit 1; }
export ANTHROPIC_BASE_URL=http://127.0.0.1:3456
export ANTHROPIC_AUTH_TOKEN=$(cat "$HOME/.claude-code-router/.gateway-key")
unset ANTHROPIC_API_KEY
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072
export ANTHROPIC_MODEL="nvidia/nemotron-3-ultra-550b-a55b"
export ANTHROPIC_DEFAULT_SONNET_MODEL="nvidia/nemotron-3-ultra-550b-a55b"
export ANTHROPIC_DEFAULT_OPUS_MODEL="nvidia/nemotron-3-ultra-550b-a55b"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="nvidia/nemotron-3.5-bolt-e4b"
setsid nohup "$HOME/.local/bin/claude" --print --settings "$HOME/workspace/micro-drama-saas/claude/settings.json" "$(cat PHASE2-FIX2-PROMPT.md)" >> logs/claude-phase2-fix2.log 2>&1 < /dev/null &
echo "phase2-fix2: PID $!"
