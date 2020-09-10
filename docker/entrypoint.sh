#!/bin/bash

function log_message {
  echo "["`date -u "+%Y-%m-%d %H:%M:%S UTC"`"]" $*
}

log_message "Migrate"
until python manage.py migrate; do
    log_message "Error in Migrate.. Retry"
    sleep 5
done
log_message "Done"

log_message "Start the worker"
python manage.py schedworker