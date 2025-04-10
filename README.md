# Discord Events Bot
## App to Create Discord Posts for Upcoming Events

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
version: '3.8'
services:
  calendar-bot:
    # Use the image built by the GitHub Action (replace with your actual path)
    image: ghcr.io/ammacdonald3/discord-bot-events:latest 
    container_name: discord-bot-events
    env_file:
      - .env # Loads variables from the .env file in the same directory
    restart: unless-stopped 
```