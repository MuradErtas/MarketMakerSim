#!/bin/sh
set -e
LISTEN="${PORT:-8080}"
sed "s/__LISTEN__/${LISTEN}/g" /deploy/nginx.railway.conf >/etc/nginx/conf.d/default.conf

cd /app
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
exec nginx -g "daemon off;"
