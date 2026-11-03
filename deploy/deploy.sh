#!/usr/bin/env bash
# Kompyuterdan serverga joylash:  bash deploy/deploy.sh <SERVER_IP>
set -euo pipefail
IP="$1"
KEY="$HOME/.ssh/oracle_bot"
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 ubuntu@$IP"
cd "$(dirname "$0")/.."
$SSH "mkdir -p ~/telegram-agent"
scp -i "$KEY" -o StrictHostKeyChecking=accept-new -q bot.py live.py voice.py requirements.txt .env caller.session "ubuntu@$IP:~/telegram-agent/"
scp -i "$KEY" -q deploy/server_setup.sh "ubuntu@$IP:~/telegram-agent/"
$SSH "bash ~/telegram-agent/server_setup.sh"
