import requests
from ics import Calendar
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import json
import re
from zoneinfo import ZoneInfo
import html
from html.parser import HTMLParser

# Load environment variables from .env file
load_dotenv()

# Fetch configuration from environment variables
CALENDAR_ICS_URL = os.getenv("CALENDAR_ICS_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Determine whether to send a message when no events are found
SEND_NO_EVENTS_MSG_STR = os.getenv("SEND_NO_EVENTS_MESSAGE", "true").lower()
SEND_NO_EVENTS_MSG = SEND_NO_EVENTS_MSG_STR != "false"

# Determine whether to send a message when an error occurs
SEND_ERROR_MSG_STR = os.getenv("SEND_ERROR_MESSAGE", "true").lower()
SEND_ERROR_MSG = SEND_ERROR_MSG_STR != "false"

# Get number of days to look ahead, default to 14, ensure it's an integer
EVENT_LOOKAHEAD_DAYS_STR = os.getenv("EVENT_LOOKAHEAD_DAYS", "14")
try:
    EVENT_LOOKAHEAD_DAYS = int(EVENT_LOOKAHEAD_DAYS_STR)
    if EVENT_LOOKAHEAD_DAYS <= 0:
        print(f"Warning: EVENT_LOOKAHEAD_DAYS ({EVENT_LOOKAHEAD_DAYS}) is not positive. Defaulting to 14.")
        EVENT_LOOKAHEAD_DAYS = 14
except ValueError:
    print(f"Warning: Invalid value '{EVENT_LOOKAHEAD_DAYS_STR}' for EVENT_LOOKAHEAD_DAYS. Must be an integer. Defaulting to 14.")
    EVENT_LOOKAHEAD_DAYS = 14

# Check if environment variables are set
if not CALENDAR_ICS_URL:
    raise ValueError("Missing CALENDAR_ICS_URL in .env file")
if not DISCORD_WEBHOOK_URL:
    raise ValueError("Missing DISCORD_WEBHOOK_URL in .env file")

# Custom HTML Parser to convert <a> to Markdown and strip other tags
class DescriptionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.current_href = None
        self.current_link_text = ""
        self.in_link = False

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.in_link = True
            # Find href attribute
            for attr, value in attrs:
                if attr == 'href':
                    self.current_href = value
                    break
        elif tag == 'br':
            # Handle <br> tags by adding a placeholder
            self.result.append('{{BR}}')
        # Ignore other start tags (effectively stripping them)

    def handle_endtag(self, tag):
        if tag == 'a':
            if self.in_link and self.current_href:
                # Clean link text (strip extra whitespace)
                cleaned_text = re.sub(r'\s+', ' ', self.current_link_text).strip()
                if cleaned_text:
                    # Escape markdown chars in text
                    cleaned_text = cleaned_text.replace('[', '\\[').replace(']', '\\]')
                    # Wrap URL in angle brackets to disable preview
                    self.result.append(f"[{cleaned_text}](<{self.current_href}>)")
                else:
                    # If link text is empty, just use the URL (wrapped)
                    self.result.append(f"<{self.current_href}>")
            # Reset link state
            self.in_link = False
            self.current_href = None
            self.current_link_text = ""
        # Ignore other end tags

    def handle_data(self, data):
        # Decode HTML entities
        decoded_data = html.unescape(data)
        if self.in_link:
            # Accumulate text within the link
            self.current_link_text += decoded_data
        else:
            # Append text outside links directly to the result list
            self.result.append(decoded_data)

# --- Function Definitions ---

# Fetches and parses the iCalendar (.ics) data from a given URL.
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

# Filters events from a Calendar object to find those occurring within a specified number of days from now.
def get_upcoming_events(calendar: Calendar, days: int) -> list:
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

# Formats a list of calendar events into a single string suitable for posting to Discord.
def format_events_message(events: list, days: int) -> str:
    """Formats the list of events into a Discord-friendly message."""
    if not events:
        # Return None if no events and we shouldn't send a message
        if not SEND_NO_EVENTS_MSG:
            return None
        # Use the actual days value in the message
        return f"No upcoming events found in the next {days} days."

    # Define the target timezone
    target_tz = ZoneInfo("America/New_York")

    # Start with the header string
    final_message = f"📅 Upcoming Events (Next {days} Days):"

    for i, event in enumerate(events):
        # Add spacing before the next event block
        final_message += "\n\n"

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

        # Add the title line for the event directly to the final message
        event_title_line = f"{event_title}: {start_time_str}{location_str}"
        final_message += event_title_line

        if event.description:
            # --- Description Processing using HTMLParser --- Start ---
            parser = DescriptionParser()
            parser.feed(event.description)
            # Join the parts from the parser
            processed_string = "".join(parser.result)
            # Replace original newlines with spaces
            desc_no_orig_nl = processed_string.replace('\r\n', ' ').replace('\n', ' ')
            # Collapse multiple spaces FIRST
            desc_cleaned_spaces = re.sub(r'\s+', ' ', desc_no_orig_nl).strip()
            # THEN replace placeholder BRs with actual newlines
            clean_desc = desc_cleaned_spaces.replace('{{BR}}', '\n')
            # --- Description Processing using HTMLParser --- End ---

            # Split into lines based on the newlines added from <br>
            lines = clean_desc.split('\n')
            cleaned_lines = []
            for line in lines:
                # Ensure lines are stripped again after splitting
                cleaned_line = line.strip()
                if cleaned_line:
                    cleaned_lines.append(cleaned_line)

            # Format as blockquote and append line-by-line
            if cleaned_lines:
                # Add newline separator between title and description block
                final_message += "\n"
                for j, line in enumerate(cleaned_lines):
                    # Check if the line is already a markdown link
                    # Simple check: starts with '[' and ends with ')' plus optional angle brackets for URL
                    if line.startswith('[') and line.endswith(')'):
                        # Apply only blockquote, no italics
                        final_message += f"> {line}"
                    else:
                        # Apply blockquote and italics
                        final_message += f"> _{line}_"
                    # Add newline after each description line except the last one
                    if j < len(cleaned_lines) - 1:
                        final_message += "\n"

    # Return the fully constructed message, stripping any edge whitespace
    return final_message.strip()

# Sends a formatted message payload to the specified Discord webhook URL.
def send_to_webhook(webhook_url: str, message: str):
    """Sends the message payload to the Discord webhook."""
    if not message:
        print("No message content to send.")
        return

    headers = {"Content-Type": "application/json"}
    payload = json.dumps({"content": message})

    try:
        print("Sending message to Discord webhook...")
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

# Main execution function: fetches calendar, gets upcoming events, formats message, and sends to Discord.
def main():
    """Main function to fetch calendar, format events, and send to webhook."""
    calendar = fetch_and_parse_calendar(CALENDAR_ICS_URL)

    if calendar:
        print("Calendar fetched successfully. Filtering events...")
        # Pass the configured number of days to get_upcoming_events
        upcoming_events = get_upcoming_events(calendar, days=EVENT_LOOKAHEAD_DAYS)
        print(f"Found {len(upcoming_events)} upcoming events for the next {EVENT_LOOKAHEAD_DAYS} days.")
        # Pass the configured number of days to format_events_message
        message = format_events_message(upcoming_events, days=EVENT_LOOKAHEAD_DAYS)

        # Only proceed if there's actually a message to send
        # (handles the case where no events are found AND SEND_NO_EVENTS_MSG is false)
        if message:
            if len(message) > 2000:
                print("Message too long, splitting...")
                # Split message carefully, ensuring webhook is called for each part
                # Estimate ~1990 chars per part to be safe with potential formatting overhead
                # Ensure the split logic doesn't break markdown or context mid-message if possible
                # Simple splitting for now:
                message_parts = [message[i:i+1990] for i in range(0, len(message), 1990)]
                for part in message_parts:
                    send_to_webhook(DISCORD_WEBHOOK_URL, part)
            else:
                send_to_webhook(DISCORD_WEBHOOK_URL, message)
        else:
             # This case means no events AND SEND_NO_EVENTS_MSG is false (because format_events_message returned None)
             print("No upcoming events found and configured not to send a message.")

    else:
        print("Failed to fetch or parse calendar. Sending failure notification...")
        if SEND_ERROR_MSG:
            error_message = "Error fetching the calendar events." 
            send_to_webhook(DISCORD_WEBHOOK_URL, error_message)
        else:
            print("Configured not to send error message to Discord.")


if __name__ == "__main__":
    print("Starting calendar event check...")
    main()
    print("Script finished.")
