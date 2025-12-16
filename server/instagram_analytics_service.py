#!/usr/bin/env python3
"""
Instagram Analytics Service
Provides comprehensive analytics for Instagram posts with caching to avoid rate limits
"""

import os
import logging
import requests
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InstagramAnalyticsService:
    """Service for Instagram analytics with caching to avoid rate limits"""
    
    def __init__(self):
        """Initialize Instagram analytics service"""
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
        self.base_url = "https://graph.facebook.com/v15.0"
        
        # Cache settings
        self.cache_duration = 300  # 5 minutes cache
        self.cache = {}
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {self.access_token}"
        }
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API request with error handling"""
        if params is None:
            params = {}
        
        params["access_token"] = self.access_token
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            try:
                error_data = response.json()
                logger.error(f"Error details: {error_data}")
                return {"error": error_data}
            except ValueError:
                logger.error(f"Response text: {response.text}")
                return {"error": str(e)}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {endpoint}: {e}")
            return {"error": str(e)}
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if not expired"""
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                logger.info(f"Using cached data for {cache_key}")
                return cached_data
            else:
                # Remove expired cache
                del self.cache[cache_key]
        return None
    
    def _set_cached_data(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Store data in cache with timestamp"""
        self.cache[cache_key] = (data, time.time())
        logger.info(f"Cached data for {cache_key}")
    
    def is_configured(self) -> bool:
        """Check if service is properly configured"""
        return bool(self.access_token and self.account_id)
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get Instagram account information"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        cache_key = f"account_info_{self.account_id}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Try to get account info - Instagram Business Account endpoint
            account_data = self._make_request(f"{self.account_id}", {
                "fields": "id,username,account_type,media_count,followers_count,follows_count"
            })
            
            if "error" in account_data:
                # If direct account access fails, try to get basic info from media endpoint
                logger.warning(f"Direct account access failed: {account_data['error']}")
                logger.info("Attempting to get account info from media endpoint...")
                
                # Try to get media list to extract account info
                media_data = self._make_request(f"{self.account_id}/media", {
                    "fields": "id",
                    "limit": 1
                })
                
                if "error" not in media_data:
                    # If we can access media, the account is valid but we can't get detailed info
                    result = {
                        "success": True,
                        "account": {
                            "id": self.account_id,
                            "username": "Instagram Account",
                            "account_type": "BUSINESS",
                            "media_count": 0,  # Will be updated by media endpoint
                            "followers_count": 0,
                            "follows_count": 0
                        },
                        "note": "Limited account info available - some fields may be restricted"
                    }
                else:
                    return {"success": False, "error": account_data["error"]}
            else:
                result = {
                    "success": True,
                    "account": {
                        "id": account_data.get("id"),
                        "username": account_data.get("username"),
                        "account_type": account_data.get("account_type"),
                        "media_count": account_data.get("media_count", 0),
                        "followers_count": account_data.get("followers_count", 0),
                        "follows_count": account_data.get("follows_count", 0)
                    }
                }
            
            self._set_cached_data(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"success": False, "error": str(e)}
    
    def get_media_list(self, limit: int = 25) -> Dict[str, Any]:
        """Get list of media posts with basic engagement data"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        cache_key = f"media_list_{self.account_id}_{limit}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get media with basic engagement fields using correct endpoint
            media_data = self._make_request(f"{self.account_id}/media", {
                "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count",
                "limit": min(limit, 100)  # Instagram API limit
            })
            
            if "error" in media_data:
                return {"success": False, "error": media_data["error"]}
            
            media_list = media_data.get("data", [])
            
            # Process media data
            processed_media = []
            for media in media_list:
                like_count = media.get("like_count", 0)
                comments_count = media.get("comments_count", 0)
                processed_media.append({
                    "id": media.get("id"),
                    "caption": media.get("caption", ""),
                    "media_type": media.get("media_type"),
                    "media_url": media.get("media_url"),
                    "permalink": f"https://instagram.com/p/{media.get('id')}/",  # Construct permalink
                    "timestamp": media.get("timestamp"),
                    "like_count": like_count,
                    "comments_count": comments_count,
                    "total_engagement": like_count + comments_count
                })
            
            result = {
                "success": True,
                "media": processed_media,
                "total_media": len(processed_media)
            }
            
            self._set_cached_data(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error getting media list: {e}")
            return {"success": False, "error": str(e)}
    
    def get_media_insights(self, media_id: str) -> Dict[str, Any]:
        """Get detailed insights for a specific media post"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        cache_key = f"media_insights_{media_id}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get media insights using the correct endpoint
            insights_data = self._make_request(f"{media_id}/insights", {
                "metric": "engagement,impressions,reach,saved,video_views"
            })
            
            if "error" in insights_data:
                logger.warning(f"Media insights failed for {media_id}: {insights_data['error']}")
                # Return empty insights rather than failing
                return {
                    "success": True,
                    "insights": {},
                    "note": "Media insights not available - may require additional permissions"
                }
            
            # Process insights data
            insights = {}
            for item in insights_data.get("data", []):
                metric_name = item.get("name")
                values = item.get("values", [])
                if values:
                    # For media insights, period is always lifetime, so get the first value
                    insights[metric_name] = values[0].get("value", 0)
            
            result = {
                "success": True,
                "insights": insights
            }
            
            self._set_cached_data(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error getting media insights for {media_id}: {e}")
            return {"success": True, "insights": {}, "note": f"Insights error: {str(e)}"}
    
    def get_account_insights(self) -> Dict[str, Any]:
        """Get account-level insights"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        cache_key = f"account_insights_{self.account_id}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get account insights using the correct endpoint
            insights_data = self._make_request(f"{self.account_id}/insights", {
                "metric": "impressions,reach,profile_views,follower_count",
                "period": "day"
            })
            
            if "error" in insights_data:
                logger.warning(f"Account insights failed: {insights_data['error']}")
                # Return empty insights rather than failing
                return {
                    "success": True,
                    "insights": {},
                    "note": "Account insights not available - may require additional permissions"
                }
            
            # Process insights data
            insights = {}
            for item in insights_data.get("data", []):
                metric_name = item.get("name")
                values = item.get("values", [])
                if values:
                    # Get the most recent value
                    insights[metric_name] = values[-1].get("value", 0)
            
            result = {
                "success": True,
                "insights": insights
            }
            
            self._set_cached_data(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error getting account insights: {e}")
            return {"success": True, "insights": {}, "note": f"Insights error: {str(e)}"}
    
    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics data for dashboard"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        cache_key = f"comprehensive_analytics_{self.account_id}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get account info
            account_info = self.get_account_info()
            if not account_info.get("success"):
                logger.warning("Account info failed, continuing with limited data")
                # Continue with limited data rather than failing completely
            
            # Get media list
            media_data = self.get_media_list(limit=25)
            if not media_data.get("success"):
                return media_data
            
            # Get account insights
            account_insights = self.get_account_insights()
            
            media_list = media_data.get("media", [])
            
            # Calculate analytics
            total_media = len(media_list)
            total_likes = sum(media.get("like_count", 0) for media in media_list)
            total_comments = sum(media.get("comments_count", 0) for media in media_list)
            total_engagement = sum(media.get("total_engagement", 0) for media in media_list)
            
            # Calculate averages
            avg_likes = total_likes / total_media if total_media > 0 else 0
            avg_comments = total_comments / total_media if total_media > 0 else 0
            avg_engagement = total_engagement / total_media if total_media > 0 else 0
            
            # Get best performing post
            best_post = max(media_list, key=lambda x: x.get("total_engagement", 0)) if media_list else {}
            
            # Get recent posts (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_posts = []
            for media in media_list:
                try:
                    post_time = datetime.fromisoformat(media.get("timestamp", "").replace("Z", "+00:00"))
                    if post_time > week_ago:
                        recent_posts.append(media)
                except:
                    continue
            
            # Media type distribution
            media_types = {}
            for media in media_list:
                media_type = media.get("media_type", "unknown")
                media_types[media_type] = media_types.get(media_type, 0) + 1
            
            analytics = {
                "success": True,
                "account": account_info.get("account", {}) if account_info.get("success") else {
                    "id": self.account_id,
                    "username": "Instagram Account",
                    "account_type": "BUSINESS",
                    "media_count": total_media,
                    "followers_count": 0,
                    "follows_count": 0
                },
                "summary": {
                    "total_media": total_media,
                    "total_likes": total_likes,
                    "total_comments": total_comments,
                    "total_engagement": total_engagement,
                    "avg_likes": round(avg_likes, 2),
                    "avg_comments": round(avg_comments, 2),
                    "avg_engagement": round(avg_engagement, 2),
                    "recent_posts_7_days": len(recent_posts)
                },
                "account_insights": account_insights.get("insights", {}),
                "media_types": media_types,
                "best_post": best_post,
                "recent_posts": recent_posts[:10],
                "all_media": media_list,
                "note": account_info.get("note", "") if account_info.get("success") else "Limited account access - some features may be restricted"
            }
            
            self._set_cached_data(cache_key, analytics)
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting comprehensive analytics: {e}")
            return {"success": False, "error": str(e)}
    
    def get_post_analytics(self, media_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific post"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        try:
            # Get media details using correct endpoint
            media_data = self._make_request(media_id, {
                "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count"
            })
            
            if "error" in media_data:
                return {"success": False, "error": media_data["error"]}
            
            # Get insights
            insights_data = self.get_media_insights(media_id)
            
            like_count = media_data.get("like_count", 0)
            comments_count = media_data.get("comments_count", 0)
            media_id = media_data.get("id")
            
            analytics = {
                "success": True,
                "post": {
                    "id": media_id,
                    "caption": media_data.get("caption", ""),
                    "media_type": media_data.get("media_type"),
                    "media_url": media_data.get("media_url"),
                    "permalink": f"https://instagram.com/p/{media_id}/",  # Construct permalink
                    "timestamp": media_data.get("timestamp"),
                    "like_count": like_count,
                    "comments_count": comments_count,
                    "total_engagement": like_count + comments_count
                },
                "insights": insights_data.get("insights", {})
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting post analytics for {media_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        self.cache.clear()
        logger.info("Instagram analytics cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        active_cache = {}
        expired_cache = {}
        
        for key, (data, timestamp) in self.cache.items():
            if current_time - timestamp < self.cache_duration:
                active_cache[key] = timestamp
            else:
                expired_cache[key] = timestamp
        
        return {
            "total_cached_items": len(self.cache),
            "active_cache_items": len(active_cache),
            "expired_cache_items": len(expired_cache),
            "cache_duration_seconds": self.cache_duration,
            "active_cache_keys": list(active_cache.keys()),
            "expired_cache_keys": list(expired_cache.keys())
        }

# Global service instance
instagram_analytics_service = InstagramAnalyticsService()

