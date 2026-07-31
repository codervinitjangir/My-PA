"""
Run this script on your LOCAL machine (where a browser is available) to get a fresh
Google OAuth token for Calendar and Gmail.

Usage:
    python tools/refresh_google_token.py

After running:
1. A browser will open for Google login
2. The token is saved to database/google_token.json
3. The base64-encoded string is printed — paste it as GOOGLE_TOKEN_B64 on Render
"""

import os
import sys
import base64

# Make sure we run from the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'database/google_token.json'

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.readonly',
]

def main():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: {CREDENTIALS_FILE} not found in {project_root}")
        print("Download it from Google Cloud Console > APIs & Services > Credentials")
        sys.exit(1)

    creds = None

    # Try to refresh existing token first
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            print("Attempting to refresh existing token...")
            try:
                creds.refresh(Request())
                print("Token refreshed successfully!")
            except Exception as e:
                print(f"Refresh failed ({e}), starting fresh auth flow...")
                creds = None

    if not creds or not creds.valid:
        print("Opening browser for Google OAuth login...")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=8080)
        print("Authentication successful!")

    # Save to disk
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())
    print(f"\nToken saved to: {TOKEN_FILE}")

    # Output base64 for Render
    token_b64 = base64.b64encode(open(TOKEN_FILE, 'rb').read()).decode()
    print("\n" + "="*60)
    print("GOOGLE_TOKEN_B64 (paste this on Render):")
    print("="*60)
    print(token_b64)
    print("="*60)
    print("\nSteps:")
    print("1. Copy the base64 string above")
    print("2. Go to Render > Your Service > Environment")
    print("3. Set GOOGLE_TOKEN_B64 = <paste string>")
    print("4. Redeploy (or just save — Render auto-restarts on env changes)")


if __name__ == '__main__':
    main()
