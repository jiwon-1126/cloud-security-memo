#!/usr/bin/env bash
# Sourceable; standalone: bash scripts/check-availability.sh URL FILE
probe_loop() {
  local url=$1 file=$2 code rc
  while true; do
    rc=0
    code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 3 "$url") || rc=$?
    printf '%s,%s,%s\n' "$(date -u +%FT%TZ)" "$code" "$rc" >> "$file"
    sleep 1
  done
}
if [[ ${BASH_SOURCE[0]} == "$0" && $# == 2 ]]; then
  probe_loop "$1" "$2"
fi
