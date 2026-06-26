from googleapiclient.discovery import build
from app.tools.base_tool import BaseTool
from app.plugins.calendar_tool import get_google_credentials

class GmailSummaryTool(BaseTool):
    name: str = "gmail_summary"
    description: str = "Get unread email count and summaries of recent important emails."

    def execute(self, query: str = None, **kwargs) -> str:
        try:
            creds = get_google_credentials()
            service = build('gmail', 'v1', credentials=creds)
            
            is_delete_request = False
            search_q = ""
            
            if query:
                q_lower = query.lower()
                if "delete" in q_lower or "trash" in q_lower or "remove" in q_lower:
                    is_delete_request = True
                
                # Extract search terms
                terms = [w for w in q_lower.split() if w not in ["delete", "trash", "remove", "mail", "email", "emails", "from", "if", "i", "have", "any", "my", "the", "a", "an", "it"]]
                if terms:
                    search_q = " ".join(terms)
            
            api_kwargs = {
                'userId': 'me',
                'maxResults': 5
            }
            if search_q:
                api_kwargs['q'] = search_q
            else:
                api_kwargs['labelIds'] = ['INBOX', 'UNREAD']
                
            # Fetch messages
            results = service.users().messages().list(**api_kwargs).execute()
            
            messages = results.get('messages', [])
            
            prefix_msg = ""
            if is_delete_request:
                prefix_msg = "For your security, I am operating in read-only mode and cannot delete emails. "
            
            if not messages:
                if search_q:
                    return prefix_msg + f"You have no emails matching '{search_q}', Sir."
                return prefix_msg + "You have no new unread emails, Sir."
                
            if search_q:
                output = [prefix_msg + f"I found {len(messages)} emails matching '{search_q}' (showing up to 5):"]
            else:
                output = [prefix_msg + f"You have {len(messages)} new unread emails (showing up to 5):"]
            
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
