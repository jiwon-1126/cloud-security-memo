#!/bin/sh
set -eu
python init_db.py
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --access-logfile - wsgi:app
