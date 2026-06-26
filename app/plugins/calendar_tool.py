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
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
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

    def execute(self, date: str = None, **kwargs) -> str:
        try:
            creds = get_google_credentials()
            service = build('calendar', 'v3', credentials=creds)
            
            tz_str = os.getenv("TIMEZONE", "Asia/Kolkata")
            tz = pytz.timezone(tz_str)
            
            if date:
                try:
                    target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                except ValueError:
                    return f"Invalid date format: {date}. Use YYYY-MM-DD."
            else:
                target_date = datetime.datetime.now(tz).date()
            
            start_of_day = tz.localize(datetime.datetime.combine(target_date, datetime.time.min))
            end_of_day = tz.localize(datetime.datetime.combine(target_date, datetime.time.max))
            
            time_min = start_of_day.isoformat()
            time_max = end_of_day.isoformat()
            
            events_result = service.events().list(
                calendarId='primary', 
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10, 
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return "No events scheduled for today, Sir."
            
            output = [f"Schedule for {target_date.strftime('%A, %b %d')}:"]
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
            return f"Error fetching calendar: {str(e)}"
