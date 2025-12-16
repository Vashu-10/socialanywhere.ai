from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, validator
from typing import Dict, Optional, Any
import asyncio
from datetime import datetime
import os
 
# Import platform adapters
from facebook_manager import facebook_manager
from twitter_adapter import TwitterAdapter  
from reddit_service import reddit_service
from reddit_oauth_helper import get_reddit_auth_url, exchange_code_for_tokens, get_reddit_user_info
from env_manager import env_manager
from fastapi.responses import RedirectResponse
import secrets
from trending_topics_service import TrendingTopicsService
 
router = APIRouter(prefix="/social-media", tags=["social-media"])
 
class PlatformCredentials(BaseModel):
    """Model for platform credentials"""
    credentials: Dict[str, str]
   
    class Config:
        # Allow extra fields for flexibility
        extra = "allow"
 
class ConnectionResponse(BaseModel):
    success: bool
    connected: bool
    message: str
    error: Optional[str] = None

class OAuth2Response(BaseModel):
    auth_url: str
    success: bool = True
    message: str = "OAuth2 flow initiated"
 
class StatusResponse(BaseModel):
    connected: bool
    has_credentials: bool
    platform: str
    last_checked: str
    details: Optional[Dict[str, Any]] = None

class TopicDetailsRequest(BaseModel):
    topic: str
    category: str

class TopicDetailsResponse(BaseModel):
    success: bool
    overview: Optional[str] = None
    key_points: Optional[list] = None
    related_topics: Optional[list] = None
    error: Optional[str] = None

# Initialize trending topics service
trending_topics_service = TrendingTopicsService()

@router.post("/trending/topic-details", response_model=TopicDetailsResponse)
async def get_topic_details(request: TopicDetailsRequest):
    """Get detailed information about a trending topic using Groq API"""
    try:
        details = trending_topics_service.get_topic_details(request.topic, request.category)
        return {
            "success": True,
            "overview": details.get("overview"),
            "key_points": details.get("key_points"),
            "related_topics": details.get("related_topics")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
 
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
FACEBOOK_REDIRECT_URI = "https://nonfeeble-fiona-retroactively.ngrok-free.dev/social-media/facebook/callback"
 
# Platform connection testers
async def test_facebook_connection(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Test Facebook connection using existing credentials.
    If user_id is provided, test all pages for that user.
    """
    try:
        creds = env_manager.check_platform_credentials('facebook')
        if not creds['has_credentials']:
            return {"connected": False, "error": "Missing required credentials"}
 
        # If user_id provided, fetch all pages for that user
        pages = []
        if user_id:
            pages = env_manager.get_facebook_pages_by_user(user_id)  # custom method
            if not pages:
                return {"connected": False, "error": f"No pages found for user {user_id}"}
        else:
            # fallback single env
            page_id = os.getenv('FACEBOOK_PAGE_ID')
            access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
            if not page_id or not access_token:
                return {"connected": False, "error": "Missing page ID or access token"}
            pages = [{"page_id": page_id, "access_token": access_token}]
 
        # Optional: quick test first page token
        import requests
        test_resp = requests.get(
            f"https://graph.facebook.com/{pages[0]['page_id']}",
            params={"access_token": pages[0]['access_token']}
        )
        connected = test_resp.status_code == 200
 
        return {
            "connected": connected,
            "details": {"pages": pages, "test_first_page": connected}
        }
 
    except Exception as e:
        return {"connected": False, "error": str(e)}
 
 
async def test_twitter_connection() -> Dict[str, Any]:
    """Test Twitter connection using existing credentials"""
    try:
        creds = env_manager.check_platform_credentials('twitter')
        if not creds['has_credentials']:
            return {"connected": False, "error": "Missing required credentials"}
       
        # Use existing TwitterAdapter to test connection
        twitter_adapter = TwitterAdapter()
       
        # Test basic authentication
        consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
        consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
        access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
       
        if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
            return {"connected": False, "error": "Missing required Twitter credentials"}
           
        return {
            "connected": True,
            "details": {
                "consumer_key": consumer_key[:10] + "...",
                "has_access_tokens": bool(access_token and access_token_secret)
            }
        }
       
    except Exception as e:
        return {"connected": False, "error": str(e)}
 
async def test_reddit_connection(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Test Reddit connection using existing credentials.
    If user_id is provided, test all Reddit accounts for that user.
    """
    try:
        creds = env_manager.check_platform_credentials('reddit')
        if not creds['has_credentials']:
            return {"connected": False, "error": "Missing required credentials"}
       
        # If user_id provided, fetch all Reddit accounts for that user
        accounts = []
        if user_id:
            accounts = env_manager.get_reddit_accounts_by_user(user_id)
            if not accounts:
                return {"connected": False, "error": f"No Reddit accounts found for user {user_id}"}
        else:
            # fallback to existing reddit_service
            status = reddit_service.get_service_status()
            if status['status'] == 'connected':
                return {"connected": True, "message": status['message']}
            else:
                return {"connected": False, "error": status['message']}
        
        # Test first account connection
        if accounts:
            # Quick test first account
            import requests
            test_resp = requests.get(
                "https://oauth.reddit.com/api/v1/me",
                headers={
                    "Authorization": f"Bearer {accounts[0]['access_token']}",
                    "User-Agent": os.getenv('REDDIT_USER_AGENT', 'SocialMediaAgent/1.0')
                },
                timeout=10
            )
            connected = test_resp.status_code == 200
            
            return {
                "connected": connected,
                "details": {"accounts": accounts, "test_first_account": connected}
            }
        else:
            return {"connected": False, "error": "No Reddit accounts found"}
       
    except Exception as e:
        return {"connected": False, "error": str(e)}
   
 
async def test_instagram_connection(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Test Instagram connection using existing credentials.
    If user_id is provided, test all Instagram accounts for that user.
    """
    try:
        creds = env_manager.check_platform_credentials('instagram')
        if not creds['has_credentials']:
            return {"connected": False, "error": "Missing required credentials"}
 
        accounts = []
        if user_id:
            accounts = env_manager.get_instagram_accounts_by_user(user_id)
            if not accounts:
                return {"connected": False, "error": f"No Instagram accounts found for user {user_id}"}
        else:
            # fallback single env
            token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
            account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
            if not token or not account_id:
                return {"connected": False, "error": "Instagram credentials not configured"}
            accounts = [{"account_id": account_id, "access_token": token}]
 
        # Quick test first account
        import requests
        test_resp = requests.get(
            f"https://graph.facebook.com/v18.0/{accounts[0]['account_id']}",
            params={"fields": "id,username", "access_token": accounts[0]['access_token']},
            timeout=10
        )
        connected = test_resp.status_code == 200
 
        return {
            "connected": connected,
            "details": {"accounts": accounts, "test_first_account": connected}
        }
 
    except Exception as e:
        return {"connected": False, "error": str(e)}
 
 
# API Routes
 
@router.get("/{platform}/status", response_model=StatusResponse)
async def get_platform_status(platform: str):
    """Get connection status for a social media platform"""
    if platform not in ["facebook", "instagram", "twitter", "reddit"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )
   
    # Test connection based on platform
    connection_testers = {
        "facebook": test_facebook_connection,
        "instagram": test_instagram_connection,
        "twitter": test_twitter_connection,
        "reddit": test_reddit_connection
    }
   
    try:
        result = await connection_testers[platform]()
        creds_check = env_manager.check_platform_credentials(platform)
       
        return StatusResponse(
            connected=result.get("connected", False),
            has_credentials=creds_check["has_credentials"],
            platform=platform,
            last_checked=datetime.now().isoformat(),
            details=result.get("details", {})
        )
       
    except Exception as e:
        return StatusResponse(
            connected=False,
            has_credentials=False,
            platform=platform,
            last_checked=datetime.now().isoformat(),
            details={"error": str(e)}
        )
 
@router.post("/{platform}/connect")
async def connect_platform(platform: str, credentials: Dict[str, str] = {}):
    """Connect to a social media platform by saving credentials"""
    if platform not in ["facebook", "instagram", "twitter", "reddit"]:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
 
    try:
        # ----- FACEBOOK FLOW -----
        if platform == "facebook":
            auth_url = (
                f"https://www.facebook.com/v19.0/dialog/oauth?"
                f"client_id={FACEBOOK_APP_ID}&redirect_uri={FACEBOOK_REDIRECT_URI}"
                f"&scope=pages_show_list,pages_read_engagement,pages_manage_posts"
                f"&response_type=code"
            )
            return OAuth2Response(auth_url=auth_url)
 
        # ----- INSTAGRAM FLOW -----
        if platform == "instagram":
            # Instagram also uses Facebook OAuth
            auth_url = (
                f"https://www.facebook.com/v19.0/dialog/oauth?"
                f"client_id={FACEBOOK_APP_ID}&redirect_uri={FACEBOOK_REDIRECT_URI}"
                f"&scope=instagram_basic,instagram_manage_insights,instagram_manage_messages"
                f"&response_type=code"
            )
            return OAuth2Response(auth_url=auth_url)
        
        # ----- REDDIT FLOW -----
        if platform == "reddit":
            # Generate random state for CSRF protection
            state = secrets.token_urlsafe(32)
            auth_url = get_reddit_auth_url(state)
            return OAuth2Response(auth_url=auth_url)
 
        # ----- OTHER PLATFORMS -----
        required_fields = {
            "twitter": ["TWITTER_CONSUMER_KEY", "TWITTER_CONSUMER_SECRET",
                        "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET",
                        "TWITTER_BEARER_TOKEN", "TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET", "TWITTER_USERNAME"]
        }
 
        if platform in required_fields:
            platform_required = required_fields[platform]
            missing_fields = [f for f in platform_required if f not in credentials or not credentials[f].strip()]
            if missing_fields:
                raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing_fields)}")
 
            valid_keys = env_manager.get_platform_env_keys(platform)
            filtered_credentials = {k: v for k, v in credentials.items() if k in valid_keys}
 
            if platform == "reddit" and "REDDIT_USER_AGENT" not in filtered_credentials:
                filtered_credentials["REDDIT_USER_AGENT"] = "SocialMediaAgent/1.0"
 
            success = env_manager.update_env_vars(filtered_credentials)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to save credentials")
 
            connection_testers = {
                "twitter": test_twitter_connection,
                "reddit": test_reddit_connection
            }
            test_result = await connection_testers[platform]()
 
            return ConnectionResponse(
                success=success,
                connected=test_result.get("connected", False),
                message=f"Successfully connected to {platform.title()}",
                error=test_result.get("error") if not test_result.get("connected") else None
            )
 
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to {platform}: {str(e)}")
 
 
 
@router.post("/{platform}/disconnect", response_model=ConnectionResponse)
async def disconnect_platform(platform: str):
    """Disconnect from a social media platform by removing credentials"""
    if platform not in ["facebook", "twitter", "reddit"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )
   
    try:
        # Get platform-specific environment keys
        keys_to_remove = env_manager.get_platform_env_keys(platform)
       
        # Remove credentials from .env file
        success = env_manager.remove_env_vars(keys_to_remove)
       
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove credentials"
            )
       
        return ConnectionResponse(
            success=True,
            connected=False,
            message=f"Successfully disconnected from {platform.title()}"
        )
       
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect from {platform}: {str(e)}"
        )
 
@router.get("/platforms")
async def get_supported_platforms():
    """Get list of supported platforms"""
    return {
        "platforms": [
            {
                "id": "facebook",
                "name": "Facebook",
                "description": "Connect your Facebook page to post content automatically",
                "required_credentials": ["FACEBOOK_PAGE_ID", "FACEBOOK_ACCESS_TOKEN"]
            },
            {
                "id": "twitter",
                "name": "Twitter",
                "description": "Connect your Twitter account to post tweets automatically",
                "required_credentials": ["TWITTER_CONSUMER_KEY", "TWITTER_CONSUMER_SECRET",
                                       "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET",
                                       "TWITTER_BEARER_TOKEN", "TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET", "TWITTER_USERNAME"]
            },
            {
                "id": "reddit",
                "name": "Reddit",
                "description": "Connect your Reddit account to post to subreddits automatically",
                "required_credentials": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
                                       "REDDIT_USERNAME", "REDDIT_PASSWORD",
                                       "REDDIT_USER_AGENT", "REDDIT_ACCESS_TOKEN", "REDDIT_REFRESH_TOKEN"]
            }
        ]
    }
 
@router.get("/status")
async def get_all_platforms_status():
    """Get connection status for all platforms"""
    platforms = ["facebook", "instagram", "twitter", "reddit"]
    status_results = {}
   
    for platform in platforms:
        try:
            # Get individual platform status
            status_response = await get_platform_status(platform)
            status_results[platform] = {
                "connected": status_response.connected,
                "has_credentials": status_response.has_credentials,
                "last_checked": status_response.last_checked,
                "details": status_response.details
            }
        except Exception as e:
            status_results[platform] = {
                "connected": False,
                "has_credentials": False,
                "last_checked": datetime.now().isoformat(),
                "error": str(e)
            }
   
    return {"platforms": status_results}
 
 
# Facebook OAuth Callback
 
@router.get("/facebook/callback")
async def facebook_callback(code: str):
    """
    Handle Facebook OAuth redirect, get long-lived token, and store multiple pages.
    """
    try:
        import httpx
        import requests
 
        # Short-lived token
        async with httpx.AsyncClient() as client:
            token_resp = await client.get(
                f"https://graph.facebook.com/v19.0/oauth/access_token?"
                f"client_id={FACEBOOK_APP_ID}&redirect_uri={FACEBOOK_REDIRECT_URI}"
                f"&client_secret={FACEBOOK_APP_SECRET}&code={code}"
            )
            token_data = token_resp.json()
        short_token = token_data.get("access_token")
        if not short_token:
            raise HTTPException(status_code=400, detail="Failed to get short-lived token")
 
        # Long-lived token
        async with httpx.AsyncClient() as client:
            long_resp = await client.get(
                f"https://graph.facebook.com/v19.0/oauth/access_token?"
                f"grant_type=fb_exchange_token&client_id={FACEBOOK_APP_ID}"
                f"&client_secret={FACEBOOK_APP_SECRET}&fb_exchange_token={short_token}"
            )
            long_data = long_resp.json()
        long_token = long_data.get("access_token")
        expires_in = long_data.get("expires_in")
        if not long_token:
            raise HTTPException(status_code=400, detail="Failed to get long-lived token")
 
        # Get user ID
        user_info = requests.get("https://graph.facebook.com/me", params={"access_token": long_token}).json()
        user_id = user_info.get("id")
 
        # Get all pages for this user
        page_resp = requests.get(f"https://graph.facebook.com/me/accounts", params={"access_token": long_token}).json()
        pages = page_resp.get("data", [])
 
        # Save main user credentials
        env_manager.update_env_vars({
            "FACEBOOK_ACCESS_TOKEN": long_token,
            "FACEBOOK_USER_ID": user_id,
            "FACEBOOK_PAGE_ID": pages[0]["id"] if pages else user_id  # Use first page or user_id as fallback
        })
        
        # Save all pages in DB (multiple accounts support)
        for p in pages:
            env_manager.save_facebook_page(user_id, p["id"], p["access_token"], expires_in)
 
        return {
            "message": f"Facebook connected successfully for user {user_id}",
            "long_lived_token": long_token,
            "expires_in": expires_in,
            "pages": pages
        }
 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
   
@router.get("/login")
async def reddit_callback(code: str, state: str):
    """
    Handle Reddit OAuth redirect and save account for user
    """
    try:
        # 1️⃣ Exchange code for tokens
        token_data = exchange_code_for_tokens(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
        scope = token_data.get("scope", "")
        
        if not access_token or not refresh_token:
            raise HTTPException(status_code=400, detail="Failed to get Reddit tokens")
        
        # 2️⃣ Get user info
        user_info = get_reddit_user_info(access_token)
        reddit_user_id = user_info.get("id")
        reddit_username = user_info.get("name")
        
        if not reddit_user_id or not reddit_username:
            raise HTTPException(status_code=400, detail="Failed to get Reddit user info")
        
        # 3️⃣ Save account (for now, use a dummy user_id)
        # In real implementation, you'd get user_id from session/auth
        user_id = "demo_user_123"  # Replace with actual user ID from auth
        
        env_manager.save_reddit_account(
            user_id=user_id,
            reddit_user_id=reddit_user_id,
            reddit_username=reddit_username,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            scopes=scope
        )
        
        return {
            "message": f"Reddit connected successfully for user {user_id}",
            "reddit_username": reddit_username,
            "reddit_user_id": reddit_user_id,
            "expires_in": expires_in,
            "scopes": scope
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/instagram/callback")
async def instagram_callback(code: str):
    """
    Handle Instagram OAuth redirect and save multiple accounts for user
    """
    import httpx, requests
    try:
        # 1️⃣ Exchange code for short-lived token
        async with httpx.AsyncClient() as client:
            token_resp = await client.get(
                f"https://graph.facebook.com/v19.0/oauth/access_token?"
                f"client_id={FACEBOOK_APP_ID}&redirect_uri={FACEBOOK_REDIRECT_URI}"
                f"&client_secret={FACEBOOK_APP_SECRET}&code={code}"
            )
            token_data = token_resp.json()
        short_token = token_data.get("access_token")
        if not short_token:
            raise HTTPException(status_code=400, detail="Failed to get short-lived token")
 
        # 2️⃣ Exchange to long-lived token
        async with httpx.AsyncClient() as client:
            long_resp = await client.get(
                f"https://graph.facebook.com/v19.0/oauth/access_token?"
                f"grant_type=fb_exchange_token&client_id={FACEBOOK_APP_ID}"
                f"&client_secret={FACEBOOK_APP_SECRET}&fb_exchange_token={short_token}"
            )
            long_data = long_resp.json()
        long_token = long_data.get("access_token")
        expires_in = long_data.get("expires_in")
        if not long_token:
            raise HTTPException(status_code=400, detail="Failed to get long-lived token")
 
        # 3️⃣ Get user info
        user_info = requests.get("https://graph.facebook.com/me", params={"access_token": long_token}).json()
        user_id = user_info.get("id")
 
        # 4️⃣ Get all Instagram accounts connected to this user
        ig_accounts_resp = requests.get(
            f"https://graph.facebook.com/{user_id}/accounts",
            params={"fields": "instagram_business_account,id,name", "access_token": long_token}
        ).json()
 
        accounts = []
        for page in ig_accounts_resp.get("data", []):
            ig_account = page.get("instagram_business_account")
            if ig_account:
                accounts.append({
                    "account_id": ig_account["id"],
                    "access_token": long_token,  # use same long-lived token
                    "name": page.get("name")
                })
                # Save each account
                env_manager.save_instagram_account(user_id, ig_account["id"], long_token, expires_in)
 
        return {
            "message": f"Instagram connected successfully for user {user_id}",
            "long_lived_token": long_token,
            "expires_in": expires_in,
            "accounts": accounts
        }
 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
 
# Save Selected Page
@router.post("/facebook/select-page")
async def select_facebook_page(payload: Dict[str, str]):
    """
    Save selected Facebook page for a specific user
    Example payload:
    {
        "user_id": "123456",
        "page_id": "987654",
        "page_access_token": "EAA..."
    }
    """
    user_id = payload.get("user_id")
    page_id = payload.get("page_id")
    page_access_token = payload.get("page_access_token")
 
    if not user_id or not page_id or not page_access_token:
        raise HTTPException(status_code=400, detail="Missing user_id, page_id, or page_access_token")
 
    env_manager.save_facebook_page(user_id, page_id, page_access_token, expires_in=60*60*24*60)  # example 60 days
 
    # Test connection
    test_result = await test_facebook_connection(user_id)
 
    return {
        "message": f"Page {page_id} connected successfully for user {user_id}!",
        "connected": test_result.get("connected", True),
        "details": test_result.get("details")
    }
 
 
 
@router.post("/reddit/select-account")
async def select_reddit_account(payload: Dict[str, str]):
    """
    Save selected Reddit account for a user
    Example payload:
    {
        "user_id": "123456",
        "reddit_user_id": "abc123",
        "reddit_username": "example_user"
    }
    """
    user_id = payload.get("user_id")
    reddit_user_id = payload.get("reddit_user_id")
    reddit_username = payload.get("reddit_username")
    
    if not user_id or not reddit_user_id or not reddit_username:
        raise HTTPException(status_code=400, detail="Missing user_id, reddit_user_id, or reddit_username")
    
    # Test connection
    test_result = await test_reddit_connection(user_id)
    
    return {
        "message": f"Reddit account {reddit_username} selected successfully for user {user_id}!",
        "connected": test_result.get("connected", True),
        "details": test_result.get("details")
    }

@router.post("/instagram/select-account")
async def select_instagram_account(payload: Dict[str, str]):
    """
    Save selected Instagram account for a user
    Example payload:
    {
        "user_id": "123456",
        "account_id": "987654",
        "access_token": "EAA..."
    }
    """
    user_id = payload.get("user_id")
    account_id = payload.get("account_id")
    access_token = payload.get("access_token")
 
    if not user_id or not account_id or not access_token:
        raise HTTPException(status_code=400, detail="Missing user_id, account_id, or access_token")
 
    env_manager.save_instagram_account(user_id, account_id, access_token, expires_in=60*60*24*60)
 
    # Test connection
    test_result = await test_instagram_connection(user_id)
 
    return {
        "message": f"Instagram account {account_id} connected successfully for user {user_id}!",
        "connected": test_result.get("connected", True),
        "details": test_result.get("details")
    }