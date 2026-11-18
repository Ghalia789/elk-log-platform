#!/bin/sh
set -eu

mkdir -p /uploads
chown app:app /uploads

exec runuser -u app -- "$@"
