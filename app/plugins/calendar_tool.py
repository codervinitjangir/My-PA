"""
Google Cloud Setup Instructions:
1. Go to https://console.cloud.google.com/
2. Create a new project or select an existing one.
3. In "APIs & Services" > "Library", search for and enable "Google Calendar API" and "Gmail API".
4. Go to "Credentials" > "Create Credentials" > "OAuth client ID".
5. Set Application type to "Desktop app".
6. Download the JSON file, rename it to "credentials.json", and place it in the root folder of this repository.
7. The first time this tool is called, a browser window will open for authentication. The token will be saved to database/google_token.json.
"""

import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pytz
from app.tools.base_tool import BaseTool

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'
]

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'database/google_token.json'

def get_google_credentials():
    import logging
    logger = logging.getLogger("J.A.R.V.I.S")
    creds = None

    # First check env var for cloud deployments (e.g. Render)
    google_token_env = os.getenv("GOOGLE_TOKEN_JSON", "").strip()
    if google_token_env:
        try:
            import json
            info = json.loads(google_token_env)
            creds = Credentials.from_authorized_user_info(info, SCOPES)
            logger.info("Loaded Google credentials from GOOGLE_TOKEN_JSON env var.")
        except Exception as e:
            logger.error(f"Failed to load GOOGLE_TOKEN_JSON from env: {e}")

    if not creds and os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        logger.info(f"Google Token file exists. Valid: {creds.valid}, Expired: {creds.expired}, Expiry: {creds.expiry}, Has Refresh Token: {bool(creds.refresh_token)}")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Token refresh failed: {e}", exc_info=True)
                print(f"Token refresh failed: {e}. Re-authenticating...")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"{CREDENTIALS_FILE} not found. Please follow the Google Cloud Setup Instructions "
                        "at the top of app/plugins/calendar_tool.py."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=8080)
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found. Please follow the Google Cloud Setup Instructions "
                    "at the top of app/plugins/calendar_tool.py."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)
        
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

class GoogleCalendarTool(BaseTool):
    name: str = "google_calendar"
    description: str = "Fetch today's calendar events and upcoming schedule from Google Calendar."

    def execute(self, date: str = None, date_string: str = None, **kwargs) -> str:
        try:
            creds = get_google_credentials()
            service = build('calendar', 'v3', credentials=creds)
            
            tz_str = os.getenv("TIMEZONE", "Asia/Kolkata")
            tz = pytz.timezone(tz_str)
            
            query = (date_string or date or "").strip().lower()
            
            if query in ["future", "upcoming", "next", "later"]:
                time_min = datetime.datetime.now(tz).isoformat()
                time_max = None
                display_date = "Upcoming Events"
            else:
                import dateparser
                target_date = datetime.datetime.now(tz).date()
                if query and query != "today":
                    parsed = dateparser.parse(query, settings={'TIMEZONE': tz_str, 'RETURN_AS_TIMEZONE_AWARE': False})
                    if parsed:
                        target_date = parsed.date()
                
                start_of_day = tz.localize(datetime.datetime.combine(target_date, datetime.time.min))
                end_of_day = tz.localize(datetime.datetime.combine(target_date, datetime.time.max))
                
                time_min = start_of_day.isoformat()
                time_max = end_of_day.isoformat()
                display_date = target_date.strftime('%A, %b %d')
            
            kwargs = {
                'calendarId': 'primary',
                'timeMin': time_min,
                'maxResults': 10,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            if time_max:
                kwargs['timeMax'] = time_max
                
            events_result = service.events().list(**kwargs).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return f"No events scheduled for {display_date}, Boss."
            
            output = [f"Schedule for {display_date}:"]
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                
                if 'T' in start:
                    dt = datetime.datetime.fromisoformat(start)
                    time_str = dt.astimezone(tz).strftime('%I:%M %p')
                else:
                    time_str = "All Day"
                    
                title = event.get('summary', 'Untitled Event')
                location = event.get('location', '')
                
                loc_str = f" at {location}" if location else ""
                output.append(f"- {time_str}: {title}{loc_str}")
                
            return "\n".join(output)
            
        except Exception as e:
            import logging
            logger = logging.getLogger("J.A.R.V.I.S")
            logger.error("calendar_tool execute failed", exc_info=True)
            raise e
