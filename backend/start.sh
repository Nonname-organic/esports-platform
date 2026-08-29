#!/bin/sh
# Render用の起動スクリプト。
# dockerCommand はシェルを介さず実行されるため、&& 連結はここで行う。
set -e

echo "== migration =="
alembic upgrade head

echo "== starting api =="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
