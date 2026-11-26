#!/bin/sh
set -eu
for key in DB_PASSWORD JWT_SECRET CSRF_SECRET TEST_USER_PASSWORD; do
  file="/run/secrets/$key"
  if [ -r "$file" ]; then
    export "$key=$(cat "$file")"
  fi
  eval 'value=${'"$key"':-}'
  if [ -z "$value" ]; then echo "Missing required setting: $key" >&2; exit 1; fi
done
unset value
exec /bin/sh /app/start.sh
