#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
state="$HOME/.local/state/memo-cd"
mkdir -p "$state"
exec 8>"$state/poll.lock"
flock -n 8 || exit 0
repo=jiwoninnuk/cloud-security-memo
channel="$repo:main-ready"
docker pull "$channel"
target=$(docker image inspect "$channel" --format '{{range .RepoDigests}}{{println .}}{{end}}' | grep -E '^jiwoninnuk/cloud-security-memo@sha256:[a-f0-9]{64}$' | head -n 1)
[[ "$target" =~ ^jiwoninnuk/cloud-security-memo@sha256:[a-f0-9]{64}$ ]]
current=$(docker service inspect -f '{{.Spec.TaskTemplate.ContainerSpec.Image}}' memo_was)
if [[ "${current##*@}" == "${target##*@}" ]]; then exit 0; fi
if [[ -f "$state/attempted" && $(cat "$state/attempted") == "$target" ]]; then echo 'Already attempted; manual retry required'; exit 0; fi
printf '%s\n' "$target" > "$state/attempted"
log="$state/deploy-$(date -u +%Y%m%dT%H%M%SZ).log"
bash ./deploy.sh "$target" 2>&1 | tee "$log"
