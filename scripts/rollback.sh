#!/usr/bin/env bash
set -euo pipefail
# Manual rollback to the previous Swarm service specification.
exec 9>"$HOME/.memo-deploy.lock"
flock -n 9
docker service rollback --detach=false memo_was
curl -fsS http://127.0.0.1/health
docker stack services memo
