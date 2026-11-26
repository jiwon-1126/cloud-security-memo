#!/usr/bin/env bash
# main called explicitly by CI; local: bash scripts/deploy.sh IMAGE
wait_ready() {
  local expected=$1 deadline=$((SECONDS+720)) state image ids id health good actual
  while (( SECONDS < deadline )); do
    state=$(docker service inspect -f '{{if .UpdateStatus}}{{.UpdateStatus.State}}{{end}}' memo_was) || return 1
    image=$(docker service inspect -f '{{.Spec.TaskTemplate.ContainerSpec.Image}}' memo_was) || return 1
    case "$state" in paused|rollback_paused|rollback_started) return 1;; esac
    [[ "$image" == "$expected" ]] || return 1
    if [[ "$state" == completed || "$state" == rollback_completed || -z "$state" ]]; then
      ids=$(docker ps -q --filter label=com.docker.swarm.service.name=memo_was)
      good=0
      for id in $ids; do
        health=$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null) || continue
        actual=$(docker inspect -f '{{.Config.Image}}' "$id" 2>/dev/null) || continue
        [[ "$health" == healthy && "${actual#docker.io/}" == "${expected#docker.io/}" ]] && good=$((good+1))
      done
      if [[ "$good" == 2 ]] && curl -fsS --max-time 5 http://127.0.0.1/health >/dev/null; then return 0; fi
    fi
    sleep 3
  done
  return 1
}
main() (
  set -euo pipefail
  local target=$1 previous current log monitor failed
  [[ "$target" =~ ^jiwoninnuk/cloud-security-memo@sha256:[a-f0-9]{64}$ ]]
  exec 9>"$HOME/.memo-deploy.lock"
  flock -n 9 || { echo 'Another deployment active'; exit 1; }
  previous=$(docker service inspect -f '{{.Spec.TaskTemplate.ContainerSpec.Image}}' memo_was)
  echo "BEFORE=$previous"
  curl -fsS --max-time 5 http://127.0.0.1/health >/dev/null
  docker pull "$target"
  log=$(mktemp)
  probe_loop http://127.0.0.1/health "$log" & monitor=$!
  finish() {
    kill "$monitor" 2>/dev/null || true
    wait "$monitor" 2>/dev/null || true
    echo 'UTC,HTTP,curl_exit'; cat "$log"
    awk -F, '{n++;if($2!=200 || $3!=0)f++} END {printf "requests=%d failures=%d\n",n,f}' "$log"
    rm -f "$log"
  }
  trap finish EXIT
  if ! docker service update --detach=true --with-registry-auth --image "$target" --update-parallelism 1 --update-order start-first --update-delay 5s --update-monitor 300s --update-failure-action rollback --rollback-parallelism 1 --rollback-order start-first memo_was || ! wait_ready "$target"; then
    echo 'Deployment failed; restoring previous image'
    current=$(docker service inspect -f '{{.Spec.TaskTemplate.ContainerSpec.Image}}' memo_was)
    if [[ "$current" != "$previous" ]]; then
      docker service update --detach=true --with-registry-auth --image "$previous" memo_was
    fi
    # Automatic Swarm rollback may still be running; wait for its completion.
    for _ in $(seq 1 240); do
      state=$(docker service inspect -f '{{.UpdateStatus.State}}' memo_was)
      [[ "$state" != rollback_started ]] && break
      sleep 3
    done
    if wait_ready "$previous"; then echo 'ROLLBACK VERIFIED'; else echo 'ROLLBACK NOT VERIFIED'; fi
    exit 1
  fi
  echo "AFTER=$(docker service inspect -f '{{.Spec.TaskTemplate.ContainerSpec.Image}}' memo_was)"
  docker stack services memo
  failed=$(awk -F, '$2!=200 || $3!=0 {f++} END{print f+0}' "$log")
  if (( failed > 0 )); then
    echo "Availability test failed; restoring previous image"
    if [[ "$target" != "$previous" ]]; then
      docker service update --detach=true --with-registry-auth --image "$previous" memo_was
      if wait_ready "$previous"; then echo "ROLLBACK VERIFIED"; else echo "ROLLBACK NOT VERIFIED"; fi
    fi
    exit 1
  fi
)
if [[ ${BASH_SOURCE[0]} == "$0" && $# == 1 ]]; then
  source "$(dirname "$0")/check-availability.sh"
  main "$1"
fi
