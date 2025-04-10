import requests
from ics import Calendar
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import json
import re
from zoneinfo import ZoneInfo

# Load environment variables from .env file
load_dotenv()
CALENDAR_ICS_URL = os.getenv('CALENDAR_ICS_URL')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Check if environment variables are set
if not CALENDAR_ICS_URL:
    raise ValueError("Missing CALENDAR_ICS_URL in .env file")
if not DISCORD_WEBHOOK_URL:
    raise ValueError("Missing DISCORD_WEBHOOK_URL in .env file")

def fetch_and_parse_calendar(url: str) -> Calendar | None:
    """Fetches the iCalendar data from the given URL and parses it."""
    try:
        response = requests.get(url)
        response.raise_for_status() 
        calendar = Calendar(response.text)
        return calendar
    except requests.exceptions.RequestException as e:
        print(f"Error fetching calendar URL: {e}")
        return None
    except Exception as e:
        print(f"Error parsing calendar data: {e}")
        return None

def get_upcoming_events(calendar: Calendar, days: int = 14) -> list:
    """Filters events from the calendar that occur within the next specified number of days."""
    now = datetime.now(timezone.utc)
    future_limit = now + timedelta(days=days)
    upcoming_events = []

    if not calendar:
        return upcoming_events

    for event in calendar.events:
        event_begin = event.begin
        if event_begin.tzinfo is None:
            event_begin = event_begin.replace(tzinfo=timezone.utc)

        if now <= event_begin < future_limit:
            upcoming_events.append(event)

    upcoming_events.sort(key=lambda e: e.begin)
    return upcoming_events

def format_events_message(events: list) -> str:
    """Formats the list of events into a Discord-friendly message."""
    if not events:
        return "No upcoming events found in the next 14 days."

    # Define the target timezone
    target_tz = ZoneInfo("America/New_York")

    # Add extra newline after header for spacing
    # Try bolding the text to enforce spacing
    message_parts = ["📅 Upcoming Events (Next 14 Days):\n"]
    for event in events:
        # Ensure event.begin is timezone-aware (should be UTC from get_upcoming_events)
        event_begin_utc = event.begin
        if event_begin_utc.tzinfo is None:
            # Fallback if somehow it's naive, assume UTC
            event_begin_utc = event_begin_utc.replace(tzinfo=timezone.utc)

        # Convert UTC time to target timezone
        event_begin_local = event_begin_utc.astimezone(target_tz)

        # Format the local time
        start_time_str = event_begin_local.strftime('%a, %b %d @ %I:%M %p %Z')

        # Use bold formatting for the event title (removing URL link logic)
        event_title = f"**{event.name}**"

        # Add location if available
        location_str = f" at {event.location}" if event.location else ""

        # Remove leading hyphen, rely on bolding and newlines for structure
        message_parts.append(f"{event_title}: {start_time_str}{location_str}")
        if event.description:
            # 1. Replace <br> tags with spaces (case-insensitive)
            desc_with_spaces = re.sub('<br\s*/?>', ' ', event.description, flags=re.IGNORECASE)
            # 2. Strip remaining HTML tags
            clean_desc = re.sub('<[^>]*>', '', desc_with_spaces)
            # 3. Replace any standard \n with spaces and clean up whitespace
            desc = clean_desc.replace('\n', ' ').strip()
            # 4. Collapse multiple spaces into single spaces
            desc = re.sub('\s+', ' ', desc).strip()
            # Add blockquote formatting and an extra newline after it
            message_parts.append(f"> _{desc}_\n") 

    # Join parts with newlines for Discord formatting
    return "\n".join(message_parts)

def send_to_webhook(webhook_url: str, message: str):
    """Sends the formatted message to the specified Discord webhook URL."""
    if not message:
        print("No message content to send.")
        return

    headers = {"Content-Type": "application/json"}
    payload = json.dumps({"content": message})

    try:
        response = requests.post(webhook_url, headers=headers, data=payload)
        response.raise_for_status() 
        print(f"Message successfully sent via webhook.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Discord webhook: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
    except Exception as e:
        print(f"An unexpected error occurred while sending webhook message: {e}")

def main():
    """Main function to fetch calendar, format events, and send to webhook."""
    print(f"Fetching calendar from {CALENDAR_ICS_URL}...")
    calendar = fetch_and_parse_calendar(CALENDAR_ICS_URL)

    if calendar:
        print("Calendar fetched successfully. Filtering events...")
        upcoming_events = get_upcoming_events(calendar, days=14)
        print(f"Found {len(upcoming_events)} upcoming events.")
        message = format_events_message(upcoming_events)

        if len(message) > 2000:
            print("Message too long, splitting...")
            message_parts = [message[i:i+1990] for i in range(0, len(message), 1990)]
            for part in message_parts:
                send_to_webhook(DISCORD_WEBHOOK_URL, part)
        else:
            send_to_webhook(DISCORD_WEBHOOK_URL, message)
    else:
        print("Failed to fetch or parse calendar. Sending failure notification...")
        error_message = "Sorry, I couldn't fetch the calendar events right now." 
        send_to_webhook(DISCORD_WEBHOOK_URL, error_message)


if __name__ == "__main__":
    print("Starting calendar event check...")
    main()
    print("Script finished.")
