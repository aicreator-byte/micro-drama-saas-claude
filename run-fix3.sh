#!/bin/bash
# Claude leg — fix round 3 (response lazy-load 500 scene/dialogue + max-6 characters). Mirrors run-fix2.sh (CCR + Nvidia).
cd "$HOME/workspace/micro-drama-saas/claude" || exit 1
bash "$HOME/infra/start-opencode-stack.sh" >> logs/claude-fix3.log 2>&1
bash start-ccr.sh >> logs/claude-fix3.log 2>&1 || exit 1
export ANTHROPIC_BASE_URL=http://127.0.0.1:3456
export ANTHROPIC_AUTH_TOKEN=$(cat "$HOME/.claude-code-router/.gateway-key")
unset ANTHROPIC_API_KEY
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072
export ANTHROPIC_MODEL="nvidia/nemotron-3-ultra-550b-a55b"
export ANTHROPIC_DEFAULT_SONNET_MODEL="nvidia/nemotron-3-ultra-550b-a55b"
export ANTHROPIC_DEFAULT_OPUS_MODEL="nvidia/nemotron-3-ultra-550b-a55b"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="nvidia/nemotron-3.5-bolt-e4b"
"$HOME/.local/bin/claude" --print --settings "$HOME/workspace/micro-drama-saas/claude/settings.json" "$(cat FIX3-PROMPT.md)" < /dev/null > logs/claude-fix3.log 2>&1
echo "claude-fix3 exit: $?" >> logs/claude-fix3.log
