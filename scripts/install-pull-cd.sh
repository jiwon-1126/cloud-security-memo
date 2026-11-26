#!/usr/bin/env bash
set -euo pipefail
[[ $(id -un) == ubuntu ]] || { echo 'Run as ubuntu'; exit 1; }
base=$(cd "$(dirname "$0")" && pwd)
sudo install -d -m 0755 /opt/memo-cd
sudo install -m 0755 "$base"/{deploy,check-availability,pull-deploy}.sh /opt/memo-cd/
sudo tee /etc/systemd/system/memo-cd.service >/dev/null <<'UNIT'
[Unit]
Description=Deploy tested memo image from Docker Hub
After=docker.service network-online.target
Wants=network-online.target
[Service]
Type=oneshot
User=ubuntu
Environment=HOME=/home/ubuntu
ExecStart=/bin/bash /opt/memo-cd/pull-deploy.sh
TimeoutStartSec=45min
UNIT
sudo tee /etc/systemd/system/memo-cd.timer >/dev/null <<'UNIT'
[Unit]
Description=Check for tested memo image
[Timer]
OnBootSec=30s
OnUnitInactiveSec=30s
Unit=memo-cd.service
[Install]
WantedBy=timers.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now memo-cd.timer
