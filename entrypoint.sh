#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Default cron schedule (e.g., daily at 8 AM) if CRON_SCHEDULE is not set
CRON_SCHEDULE=${CRON_SCHEDULE:="0 8 * * *"}

# The command to be executed by cron
COMMAND="python /app/bot.py >> /proc/1/fd/1 2>/proc/1/fd/2"

# Echo the cron schedule and command into the cron file
# Note: Ensure root user runs the cron job
# Adding a newline at the end is required by cron
echo "$CRON_SCHEDULE root $COMMAND" > /etc/cron.d/bot-cron
echo "" >> /etc/cron.d/bot-cron # Add required empty line

# Set the correct permissions on the cron file
chmod 0644 /etc/cron.d/bot-cron

# Optional: Register the crontab (may not be strictly necessary with cron.d)
# crontab /etc/cron.d/bot-cron

echo "Starting cron daemon with schedule: '$CRON_SCHEDULE'"

# Start cron in the foreground (becomes the main process)
exec cron -f
