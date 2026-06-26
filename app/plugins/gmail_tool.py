from googleapiclient.discovery import build
from app.tools.base_tool import BaseTool
from app.plugins.calendar_tool import get_google_credentials

class GmailSummaryTool(BaseTool):
    name: str = "gmail_summary"
    description: str = "Get unread email count and summaries of recent important emails."

    def execute(self, **kwargs) -> str:
        try:
            creds = get_google_credentials()
            service = build('gmail', 'v1', credentials=creds)
            
            # Fetch unread messages
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX', 'UNREAD'],
                maxResults=5
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return "You have no new unread emails, Sir."
                
            output = [f"You have {len(messages)} new unread emails (showing up to 5):"]
            
            for msg in messages:
                msg_data = service.users().messages().get(
                    userId='me', 
                    id=msg['id'], 
                    format='metadata', 
                    metadataHeaders=['Subject', 'From']
                ).execute()
                
                headers = msg_data.get('payload', {}).get('headers', [])
                subject = "No Subject"
                sender = "Unknown Sender"
                
                for header in headers:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                    elif header['name'].lower() == 'from':
                        sender = header['value']
                        # Clean up sender format like "Name <email@domain.com>"
                        if '<' in sender:
                            sender = sender.split('<')[0].strip()
                
                snippet = msg_data.get('snippet', '')
                if len(snippet) > 100:
                    snippet = snippet[:97] + "..."
                    
                output.append(f"- From: {sender}")
                output.append(f"  Subject: {subject}")
                output.append(f"  Snippet: {snippet}")
                
            return "\n".join(output)
            
        except Exception as e:
            return f"Error fetching emails: {str(e)}"
