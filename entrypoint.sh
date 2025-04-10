#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Default cron schedule (e.g., daily at 8 AM) if CRON_SCHEDULE is not set
CRON_SCHEDULE=${CRON_SCHEDULE:="0 8 * * *"}


# The command to be executed by cron - use the full path to python
COMMAND="/usr/local/bin/python /app/bot.py >> /proc/1/fd/1 2>/proc/1/fd/2"

# Write environment variables to /etc/environment so cron jobs can source them
# Use env expansion: if VAR is not set or null, use empty string "".
# Ensure the file is created fresh each time
echo "CALENDAR_ICS_URL=\"${CALENDAR_ICS_URL:-}\"" > /etc/environment
echo "DISCORD_WEBHOOK_URL=\"${DISCORD_WEBHOOK_URL:-}\"" >> /etc/environment
# Add TZ as well if it's set, for consistency within the script if needed later
echo "TZ=\"${TZ:-UTC}\"" >> /etc/environment


# Echo the cron schedule and command into the cron file
# The '.' command sources the /etc/environment file before running the command
echo "# Cron job definition" > /etc/cron.d/bot-cron
echo "$CRON_SCHEDULE root . /etc/environment; $COMMAND" >> /etc/cron.d/bot-cron 
echo "" >> /etc/cron.d/bot-cron # Add required empty line

# Set the correct permissions on the cron file
chmod 0644 /etc/cron.d/bot-cron

# Optional: Register the crontab (may not be strictly necessary with cron.d)
# crontab /etc/cron.d/bot-cron

echo "Starting cron daemon with schedule: '$CRON_SCHEDULE'"
echo "Environment variables written to /etc/environment for cron job:"
# Print the content for debugging (optional)
cat /etc/environment

# Start cron in the foreground (becomes the main process)
exec cron -f
