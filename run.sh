#!/bin/bash
# Claude Code leg — Micro Drama SaaS independent MVP build.
# Runs Claude Code non-interactively via Claude Code Router (CCR) on
# 127.0.0.1:3456, which translates Anthropic /v1/messages -> Nvidia NIM
# (OpenAI format). Model: nvidia/nemotron-3-ultra-550b-a55b (direct NIM,
# proven working; the same model via 9Router 404s). Background/haiku calls
# use the small nemotron-3.5-bolt-e4b. API key = Nvidia key from the vault
# (custom.nvidia surrogate stored in CCR config, resolved by egress proxy).
# 9Router path kept as fallback only: cf quota exhausted until 07:00 WIB.
# Config per tutorial + official Claude docs:
# - ANTHROPIC_BASE_URL = gateway root, NO /v1 (Claude appends /v1/messages)
# - ANTHROPIC_AUTH_TOKEN (Bearer) = CCR gateway client key; ANTHROPIC_API_KEY
#   unset so Claude does not treat it as a first-party Anthropic credential
# - all model tiers pinned (background/subagent calls otherwise request a
#   real claude-haiku/opus model the gateway cannot serve)
# - CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
# - CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072 (conservative for ultra-550b;
#   docs: for an unrecognized gateway ID this var applies on its own)
# - prompt = CLAUDE-PROMPT.md (PROMPT.md + anti-copy addendum: build ONLY
#   inside claude/, NEVER read/copy ../hermes/ or ../opencode/. First run
#   13:12 WIB exited 0 in ~10 min with a report describing the Hermes leg
#   and zero files in claude/ — a fake completion, hence the addendum.)
cd "$HOME/workspace/micro-drama-saas/claude" || exit 1
bash "$HOME/infra/start-opencode-stack.sh" >> logs/claude-build.log 2>&1
bash start-ccr.sh >> logs/claude-build.log 2>&1 || exit 1
export ANTHROPIC_BASE_URL=http://127.0.0.1:3456
export ANTHROPIC_AUTH_TOKEN=$(cat "$HOME/.claude-code-router/.gateway-key")
unset ANTHROPIC_API_KEY
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072
export ANTHROPIC_MODEL="nvidia/nemotron-3-ultra-550b-a55b"
export ANTHROPIC_DEFAULT_SONNET_MODEL="nvidia/nemotron-3-ultra-550b-a55b"
export ANTHROPIC_DEFAULT_OPUS_MODEL="nvidia/nemotron-3-ultra-550b-a55b"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="nvidia/nemotron-3.5-bolt-e4b"
"$HOME/.local/bin/claude" --print --settings "$HOME/workspace/micro-drama-saas/claude/settings.json" "$(cat CLAUDE-PROMPT.md)" < /dev/null > logs/claude-build.log 2>&1
echo "claude exit: $?" >> logs/claude-build.log
