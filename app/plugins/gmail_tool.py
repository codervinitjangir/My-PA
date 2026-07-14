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
                    return prefix_msg + f"You have no emails matching '{search_q}', Boss."
                return prefix_msg + "You have no new unread emails, Boss."
                
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

    def get_latest_attachment(self, file_type: str = "pdf") -> dict:
        """
        Finds and downloads the attachment from the most recent email
        that contains a file matching file_type (e.g. "pdf", "docx", "xlsx").
        """
        try:
            import base64
            creds = get_google_credentials()
            service = build('gmail', 'v1', credentials=creds)

            query = f"has:attachment filename:{file_type}"
            results = service.users().messages().list(userId='me', maxResults=20, q=query).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return {"found": False, "error": f"No emails found with {file_type} attachment."}
                
            msg_id = messages[0]['id']
            msg_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            headers = msg_data.get('payload', {}).get('headers', [])
            subject = "No Subject"
            sender = "Unknown Sender"
            for header in headers:
                if header['name'].lower() == 'subject':
                    subject = header['value']
                elif header['name'].lower() == 'from':
                    sender = header['value']
                    if '<' in sender:
                        sender = sender.split('<')[0].strip()

            def find_attachment(parts):
                for part in parts:
                    filename = part.get('filename', '').lower()
                    if filename and filename.endswith(f".{file_type.lower()}") and part.get('body', {}).get('attachmentId'):
                        return filename, part['body']['attachmentId']
                    if 'parts' in part:
                        res = find_attachment(part['parts'])
                        if res:
                            return res
                return None, None

            parts = msg_data.get('payload', {}).get('parts', [])
            filename, attachment_id = find_attachment(parts)
            
            if not attachment_id:
                # Some emails don't have parts list but directly attachment in payload (rare but possible)
                filename = msg_data.get('payload', {}).get('filename', '').lower()
                if filename and filename.endswith(f".{file_type.lower()}") and msg_data.get('payload', {}).get('body', {}).get('attachmentId'):
                    attachment_id = msg_data['payload']['body']['attachmentId']
            
            if not attachment_id:
                return {"found": False, "error": "Attachment part not found in message payload."}
                
            attachment = service.users().messages().attachments().get(
                userId='me', messageId=msg_id, id=attachment_id
            ).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'])
            size_mb = len(file_data) / (1024 * 1024)
            
            return {
                "found": True,
                "filename": filename,
                "data": file_data,
                "sender": sender,
                "subject": subject,
                "size_mb": size_mb
            }
        except Exception as e:
            return {"found": False, "error": str(e)}
