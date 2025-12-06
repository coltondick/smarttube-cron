#!/bin/sh

# Default to 3 AM if the variable isn't set
SCHEDULE=${CRON_SCHEDULE:-"0 3 * * *"}

echo "Setting up cron job with schedule: $SCHEDULE"

# Write the cron line dynamically
echo "$SCHEDULE /usr/local/bin/python /app/install.py >> /proc/1/fd/1 2>&1" > /app/crontab

# Register the crontab
crontab /app/crontab

# Wait until at least DEVICE is present, then write env vars
until [ -n "$DEVICE" ]; do
  echo "Waiting for environment variables..."
  sleep 1
done

# Export vars for use by cron (so the python script can see DEVICE)
printenv | grep -E '^(DEVICE)=' > /tmp/env_vars

# Start cron in foreground
cron -f