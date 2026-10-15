#!/usr/bin/env bash
set -euo pipefail
account="${1:?account required}"
case "$account" in christine|jaron) ;; *) exit 2 ;; esac
export CODEX_HOME="/root/.config/pumpkin-parity-lab/accounts/$account"
unset OPENAI_API_KEY CODEX_API_KEY OPENAI_BASE_URL OPENAI_ORG_ID
cd /root/pumpkin-parity-lab
exec /root/.local/bin/codex exec --ignore-user-config --model gpt-6.1-sol \
  --sandbox danger-full-access -c approval_policy=never \
  -c model_reasoning_effort=high -c features.multi_agent=false \
  --json --output-last-message "artifacts/$account-completion.md" \
  - < "ops/$account-task.txt"
