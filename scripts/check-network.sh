#!/usr/bin/env bash
set -euo pipefail
# Local Compose; run from project directory on Docker host.
web=$(docker compose ps -q web); was=$(docker compose ps -q was); db=$(docker compose ps -q db)
[[ -n "$web" && -n "$was" && -n "$db" ]]
echo '=== Published ports ==='
for id in "$web" "$was" "$db"; do docker inspect -f '{{.Name}} {{json .HostConfig.PortBindings}}' "$id"; done
echo '=== Web network namespace -> WAS positive control ==='
probe() { docker run --rm --network "container:$web" --entrypoint python cloud-security-memo:local -c "$1" "${@:2}"; }
probe 'import socket; s=socket.create_connection(("was",5000),3); s.close(); print("PASS: Web -> WAS")'
echo '=== WAS -> DB positive control ==='
docker exec "$was" python -c 'import socket; s=socket.create_connection(("db",3306),3); s.close(); print("PASS: WAS -> DB")'
dbip=$(docker exec "$was" python -c 'import socket; print(socket.gethostbyname("db"))')
echo '=== Web -> DB direct IP (expected blocked) ==='
probe 'import socket,sys; exec("try:\n s=socket.create_connection((sys.argv[1],3306),3)\nexcept OSError as e:\n print(\"PASS: connection blocked: \" + str(e))\nelse:\n s.close(); raise SystemExit(1)")' "$dbip"
echo '=== Network membership ==='
for id in "$web" "$was" "$db"; do docker inspect -f '{{.Name}} {{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$id"; done
curl -fsS http://localhost/health; echo
