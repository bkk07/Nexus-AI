"""Walks Gmail MIME payloads, extracting text/html parts and headers."""

import base64
from typing import Dict, Tuple

def extract_body_and_headers(message: dict) -> Tuple[Dict[str, str], str, bool]:
    """Extracts headers, body text, and a boolean indicating if it's HTML."""
    payload = message.get("payload", {})
    headers_list = payload.get("headers", [])
    
    # 1. Extract Headers
    headers = {
        header["name"]: header["value"] 
        for header in headers_list 
        if header["name"] in ("From", "To", "Subject", "Date")
    }
    
    # 2. Extract Body
    def _get_body(parts: list) -> Tuple[str, bool]:
        text_body = ""
        html_body = ""
        
        for part in parts:
            mime_type = part.get("mimeType")
            data = part.get("body", {}).get("data", "")
            
            if data:
                # Safely pad base64 string before decoding to prevent padding errors
                pad_len = len(data) % 4
                if pad_len:
                    data += '=' * (4 - pad_len)
                    
                if mime_type == "text/plain":
                    text_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                elif mime_type == "text/html":
                    html_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    
            if "parts" in part:
                # Recursively search multipart payloads
                nested_text, nested_html = _get_body(part["parts"])
                if nested_text: text_body = nested_text
                if nested_html: html_body = nested_html
                
        # Prefer HTML if available, so it can be cleanly sanitized later
        if html_body:
            return html_body, True
        return text_body, False

    parts = payload.get("parts", [payload])
    raw_body, is_html = _get_body(parts)
    
    return headers, raw_body, is_html