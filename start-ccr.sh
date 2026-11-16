#!/bin/bash
# Ensure the Claude Code Router gateway (127.0.0.1:3456) is running.
# CCR translates Anthropic /v1/messages -> Nvidia NIM (OpenAI format).
# Survives VM swaps: run.sh calls this before launching claude.
export PATH="$HOME/.local/bin:$PATH"
if curl -s --max-time 5 -o /dev/null http://127.0.0.1:3456/v1/models; then
  echo "ccr: gateway already up"
  exit 0
fi
echo "ccr: starting gateway..."
setsid nohup ccr start --no-open --host 127.0.0.1 --port 3458 >> logs/ccr-serve.log 2>&1 < /dev/null &
for i in $(seq 1 30); do
  if curl -s --max-time 5 -o /dev/null http://127.0.0.1:3456/v1/models; then
    echo "ccr: gateway up after ${i}s"
    exit 0
  fi
  sleep 2
done
echo "ccr: gateway FAILED to come up" >&2
exit 1
