"""
Reddit OAuth2 Helper Functions
Implements dynamic Reddit OAuth2 flow similar to Facebook/Instagram
"""

import os
import requests
import base64
from typing import Dict, Optional, List
from datetime import datetime, timedelta

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_REDIRECT_URI = os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8000/login")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "SocialMediaAgent/1.0 by u/SuspiciousPapaya3497")

def get_reddit_auth_url(state: str, scopes: List[str] = None) -> str:
    """
    Generate Reddit OAuth authorization URL
    
    Args:
        state: Random state string for CSRF protection
        scopes: List of permission scopes (default: identity, read, submit)
    
    Returns:
        Authorization URL string
    """
    if scopes is None:
        scopes = ["identity", "read", "submit", "subscribe", "vote"]
    
    scope_string = " ".join(scopes)
    
    auth_url = (
        f"https://www.reddit.com/api/v1/authorize?"
        f"client_id={REDDIT_CLIENT_ID}"
        f"&response_type=code"
        f"&state={state}"
        f"&redirect_uri={REDDIT_REDIRECT_URI}"
        f"&duration=permanent"  # Request permanent refresh token
        f"&scope={scope_string}"
    )
    
    return auth_url
    
def exchange_code_for_tokens(code: str) -> Dict:
    """
    Exchange authorization code for access and refresh tokens
    
    Args:
        code: Authorization code from Reddit callback
    
    Returns:
        Dict with access_token, refresh_token, expires_in, scope
    """
    # Reddit requires HTTP Basic Authentication
    auth_string = f"{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "User-Agent": REDDIT_USER_AGENT
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDDIT_REDIRECT_URI
    }
    
    response = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        headers=headers,
        data=data
    )
    
    response.raise_for_status()
    return response.json()

def refresh_access_token(refresh_token: str) -> Dict:
    """
    Use refresh token to get new access token
    
    Args:
        refresh_token: Valid refresh token
    
    Returns:
        Dict with new access_token and expires_in
    """
    auth_string = f"{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "User-Agent": REDDIT_USER_AGENT
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    response = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        headers=headers,
        data=data
    )
    
    response.raise_for_status()
    return response.json()

def get_reddit_user_info(access_token: str) -> Dict:
    """
    Get authenticated user's Reddit profile info
    
    Args:
        access_token: Valid access token
    
    Returns:
        Dict with user profile data (id, name, etc.)
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": REDDIT_USER_AGENT
    }
    
    response = requests.get(
        "https://oauth.reddit.com/api/v1/me",
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()

def is_token_expired(expires_at: datetime) -> bool:
    """Check if token has expired"""
    return datetime.now() >= expires_at

def get_valid_access_token(account_data: Dict) -> str:
    """
    Get valid access token, refreshing if necessary
    
    Args:
        account_data: Dict with access_token, refresh_token, expires_at
    
    Returns:
        Valid access token string
    """
    expires_at = account_data.get("expires_at")
    
    # If token expires in less than 5 minutes, refresh it
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    
    if is_token_expired(expires_at - timedelta(minutes=5)):
        # Refresh the token
        refresh_token = account_data.get("refresh_token")
        token_data = refresh_access_token(refresh_token)
        
        # Note: Reddit refresh tokens are consumed and new ones issued
        # Update your database with new tokens here
        return token_data["access_token"]
    
    return account_data["access_token"]