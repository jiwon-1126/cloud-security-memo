#!/usr/bin/env bash
set -euo pipefail
# Run on the Swarm manager. Select the actual DB node explicitly.
node=${1:?Usage: bash scripts/init.sh DB_NODE_NAME}
docker node inspect "$node" >/dev/null
docker node update --label-add memo_db=true "$node" >/dev/null
for key in DB_PASSWORD DB_ROOT_PASSWORD JWT_SECRET CSRF_SECRET TEST_USER_PASSWORD; do
  if docker secret inspect "$key" >/dev/null 2>&1; then
    echo "Keeping existing secret: $key"; continue
  fi
  if [[ "$key" == JWT_SECRET || "$key" == CSRF_SECRET || "$key" == DB_ROOT_PASSWORD || "$key" == DB_PASSWORD ]]; then
    value=$(openssl rand -hex 32)
  else
    read -r -s -p "Enter evaluation test password: " value; echo
  fi
  [[ -n "$value" ]] || exit 1
  printf '%s' "$value" | docker secret create "$key" - >/dev/null
  unset value
done
