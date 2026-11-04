#!/bin/sh
# Railway: qo'ng'iroqchi akkaunt sessiyasini CALLER_SESSION_B64 o'zgaruvchisidan tiklaydi.
# Volume /data ulangan bo'lsa, sessiya o'sha yerda saqlanadi (qayta joylashda yo'qolmaydi).
set -e
DIR=/app
[ -d /data ] && DIR=/data
if [ ! -f "$DIR/caller.session" ] && [ -n "$CALLER_SESSION_B64" ]; then
  # gzip bilan siqilgan bo'lsa ochadi, aks holda oddiy base64
  if ! echo "$CALLER_SESSION_B64" | base64 -d | gunzip -c > "$DIR/caller.session" 2>/dev/null; then
    echo "$CALLER_SESSION_B64" | base64 -d > "$DIR/caller.session"
  fi
fi
[ "$DIR" != /app ] && ln -sf "$DIR/caller.session" /app/caller.session
exec python bot.py
