#!/bin/sh
exec python3 "$(dirname "$0")/paste.py" all "$@"
