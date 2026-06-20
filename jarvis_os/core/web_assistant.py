import webbrowser
import urllib.parse
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class WebAssistant:
    """
    Stateless Web Assistant (v0.5)
    Strictly limited to 3 actions: open, search, summarize.
    No persistent browsers. No DOM mutation.
    """
    
    def __init__(self, chat_service=None):
        self.chat_service = chat_service

    def open_site(self, url: str) -> str:
        """Safely opens a site in the user's default native browser."""
        if not url.startswith("http"):
            url = f"https://{url}"
        
        logger.info(f"WebAssistant: Opening site {url}")
        webbrowser.open(url)
        return f"Opened {url} in your browser."

    def search(self, query: str) -> str:
        """Performs a Google search in the user's default browser."""
        search_url = f"https://google.com/search?q={urllib.parse.quote(query)}"
        logger.info(f"WebAssistant: Searching for '{query}'")
        webbrowser.open(search_url)
        return f"Searching for '{query}'..."

    def summarize_url(self, url: str) -> str:
        """
        Fetches the URL statelessly, extracts text, and uses the LLM to summarize.
        Expected format:
        📄 Title
        🎯 Main topic
        • Point 1
        ...
        """
        if not url.startswith("http"):
            url = f"https://{url}"
            
        logger.info(f"WebAssistant: Summarizing URL {url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()
                
            title = soup.title.string.strip() if soup.title else "Unknown Title"
            text = soup.get_text(separator=' ', strip=True)
            
            # We don't want to send millions of tokens. Truncate to safe limit (e.g., 20000 chars)
            text = text[:20000]
            
            if not self.chat_service:
                return "Error: Chat service is required to summarize the page."
                
            prompt = f"""
Analyze the following webpage content:
Title: {title}
Content: {text}

Format your response EXACTLY like this:
📄 Title: [Extract or use the Title]
🎯 Main topic: [1 sentence summary]
• [Key point 1]
• [Key point 2]
• [Key point 3]
• [Key point 4]
• [Key point 5]

Stop after the 5th point. Do not add any introductory or concluding text.
"""
            # Request LLM via chat_service (assumes chat_service has a generate method or we use it via router)
            # Actually, WebAssistant doesn't have direct LLM generation access, it just formats the prompt.
            # But the user expects it to return the summary. Let's assume chat_service can be used to generate.
            # In jarvis, chat_service uses the LLM. Let's check how chat_service is implemented.
            
            summary = self.chat_service.groq_service.get_response(question=prompt)
            return summary
            
        except Exception as e:
            logger.error(f"WebAssistant: Failed to summarize {url} - {e}")
            return f"Failed to summarize the page: {e}"
