"""
J.A.R.V.I.S. APPLICATION PACKAGE
-------------------------------
This directory is the main Python package for the J.A.R.V.I.S. backend.


# Functional Imports - Ye ab actually kaam karega
from .main import app
from .models import ChatRequest
from .services.chat_service import ChatService

# Metadata (Optional but good practice)
__version__ = "1.0.0"
__all__ = ["app", "ChatRequest", "ChatService"]
"""