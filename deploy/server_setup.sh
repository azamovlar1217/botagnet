#!/usr/bin/env bash
# Serverda bir marta ishga tushiriladi: Python, ffmpeg, kutubxonalar va systemd xizmati.
set -euo pipefail
APP=/home/ubuntu/telegram-agent
sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 python3-venv python3-pip ffmpeg
# 1 GB RAM li serverlar uchun swap
if [ ! -f /swapfile ] && [ "$(free -m | awk '/Mem:/{print $2}')" -lt 2000 ]; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi
cd "$APP"
[ -d venv ] || python3 -m venv venv
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt
chmod 600 .env caller.session
sudo tee /etc/systemd/system/telegram-agent.service >/dev/null <<UNIT
[Unit]
Description=Telegram AI agent
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=$APP
ExecStart=$APP/venv/bin/python bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable telegram-agent >/dev/null
sudo systemctl restart telegram-agent
sleep 8
systemctl is-active telegram-agent
journalctl -u telegram-agent -n 5 --no-pager | sed -E 's/[0-9]{8,}:[A-Za-z0-9_-]+/***/g'
