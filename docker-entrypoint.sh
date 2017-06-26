#!/bin/bash
set -e

if [ "$1" = 'uwsgi' -a "$(id -u)" = '0' ]; then
    export UWSGI_HTTP=:${PORT}

    set -- gosu pipet tini -- "$@"
fi

exec "$@"
