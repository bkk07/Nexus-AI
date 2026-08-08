"""Strips scripts, styles, tracking pixels, and boilerplate from email HTML."""

import re
from bs4 import BeautifulSoup

_TRACKING_PIXEL_ATTRS = ("width=\"1\"", "height=\"1\"", "1x1", "spacer.gif")

class HTMLSanitizer:
    """Removes HTML bloat and outputs clean, readable plaintext."""
    
    def strip(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove entire standard noise tags
        for tag in soup(["script", "style", "head", "meta", "link"]):
            tag.decompose()
            
        # Target and remove tracking pixels
        for img in soup.find_all("img"):
            width = img.get("width", "")
            height = img.get("height", "")
            src = img.get("src", "")
            
            if str(width) == "1" or str(height) == "1" or any(marker in src for marker in _TRACKING_PIXEL_ATTRS):
                img.decompose()
                
        # Strip inline classes and styles that can leak into text dumps
        for tag in soup.find_all(style=True):
            del tag["style"]
        for tag in soup.find_all(class_=True):
            del tag["class"]
            
        text = soup.get_text(separator="\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()