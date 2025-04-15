# Discord Events Bot
This is an app to create Discord posts for upcoming events on a Google Calendar. It requires both a Google Calendar ICS link and a Discord webhook URL. For security, these variables should be set in a .env file alongside docker-compose.yml, while other variables can be set directly in docker-compose.yml.

### Sample .env File:
The .env file should be placed in the root directory of the project alongside the docker-compose.yml file.
```
# Public ICS link for your Google Calendar
CALENDAR_ICS_URL="<ICS_URL>"

# Discord Webhook URL
DISCORD_WEBHOOK_URL="<WEBHOOK_URL>"
```

### Sample docker-compose.yml File:
```yaml
# docker-compose.yml
services:
  calendar-bot:
    image: ghcr.io/ammacdonald3/discord-bot-events:latest 
    container_name: discord-bot-events
    env_file:
      - .env # Loads variables from the .env file in the same directory
    environment:
      - TZ=America/New_York 
      # Frequency to retrieve events and send Discord message
      - CRON_SCHEDULE=0 17 * * 0 
      # Number of days to look ahead for events
      - EVENT_LOOKAHEAD_DAYS=14
      # Whether to send a message when no events are found
      - SEND_NO_EVENTS_MESSAGE=false
      # Whether to send a message when an error occurs
      - SEND_ERROR_MESSAGE=false
    restart: unless-stopped 
```