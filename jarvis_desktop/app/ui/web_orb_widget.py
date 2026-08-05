# jarvis_desktop/app/ui/web_orb_widget.py

import json
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor
from PySide6.QtWebEngineCore import QWebEngineSettings

class WebOrbWidget(QWidget):
    """
    Wrapper for QWebEngineView that loads the Next.js Ultron Orb UI
    and exposes the exact same API as the original OrbWidget.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # We don't want it to be transparent for mouse events, because the user wants to interact with it!
        # self.setAttribute(Qt.WA_TransparentForMouseEvents) 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView(self)
        
        # Transparent background for the webview itself, so the scanlines show through
        self.web_view.page().setBackgroundColor(QColor(Qt.transparent))
        
        # Enable WebGL
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        # Enable media (webcam)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        
        # Handle media capture requests (Webcam)
        self.web_view.page().featurePermissionRequested.connect(self.on_feature_permission_requested)
        
        # Load the dev server url for now
        self.web_view.setUrl(QUrl("http://localhost:3000"))
        
        layout.addWidget(self.web_view)
        
        self._voice_state = "online"
        
    def on_feature_permission_requested(self, url, feature):
        # Auto-grant webcam access
        from PySide6.QtWebEngineCore import QWebEnginePage
        if feature == QWebEnginePage.Feature.MediaVideoCapture:
            self.web_view.page().setFeaturePermission(url, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)
            
    def set_voice_state(self, state: str):
        """
        Sends the voice state update down into the Next.js UI via postMessage
        """
        self._voice_state = state.lower()
        payload = json.dumps({"type": "voice_state", "state": self._voice_state})
        js_code = f"window.postMessage({payload}, '*');"
        self.web_view.page().runJavaScript(js_code)
