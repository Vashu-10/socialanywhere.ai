#!/usr/bin/env python3
"""
Twitter Analytics Service
Provides comprehensive analytics for your own Twitter posts using API v2 free tier
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

class TwitterAnalyticsService:
    """Service for Twitter analytics and account data using API v2"""
    
    def __init__(self):
        """Initialize Twitter analytics service"""
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
        self.consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.username = os.getenv('TWITTER_USERNAME', 'shephertz1')
        
        self.base_url = "https://api.twitter.com/2"
        self.user_id = None
        
        # Rate limiting and caching
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_window = 15 * 60  # 15 minutes in seconds
        self.max_requests_per_window = 800  # Conservative limit (900 - 100 buffer)
        self.cache = {}
        self.cache_duration = 5 * 60  # 5 minutes cache
        self.last_successful_data = {}  # Store last successful data for fallback
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API v2 requests"""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make a request without hitting rate limits"""
        current_time = time.time()
        
        # Reset counter if we're in a new window
        if current_time - self.last_request_time > self.rate_limit_window:
            self.request_count = 0
            self.last_request_time = current_time
        
        # Check if we've exceeded the limit
        if self.request_count >= self.max_requests_per_window:
            logger.warning(f"Rate limit reached: {self.request_count}/{self.max_requests_per_window}")
            return False
        
        return True
    
    def _make_request(self, url: str, params: Dict = None, headers: Dict = None) -> requests.Response:
        """Make a rate-limited request to Twitter API"""
        if not self._check_rate_limit():
            # Return a mock 429 response
            response = requests.Response()
            response.status_code = 429
            response._content = b'{"title":"Too Many Requests","detail":"Rate limit exceeded"}'
            return response
        
        # Make the actual request
        response = requests.get(url, params=params, headers=headers)
        self.request_count += 1
        self.last_request_time = time.time()
        
        return response
    
    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """Get cached data if it's still valid"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_duration:
                return data
            else:
                del self.cache[key]
        return None
    
    def _cache_data(self, key: str, data: Dict):
        """Cache data with timestamp"""
        self.cache[key] = (data, time.time())
    
    def _get_oauth_auth(self):
        """Get OAuth 1.0a authentication for API v1.1 requests"""
        try:
            from requests_oauthlib import OAuth1
            return OAuth1(
                self.consumer_key,
                self.consumer_secret,
                self.access_token,
                self.access_token_secret
            )
        except ImportError:
            logger.error("requests_oauthlib not installed. Install with: pip install requests-oauthlib")
            return None
    
    def _get_user_id(self) -> Optional[str]:
        """Get Twitter user ID from username"""
        if self.user_id:
            return self.user_id
            
        # Try OAuth 1.0a first (more reliable)
        auth = self._get_oauth_auth()
        if auth:
            try:
                # Use API v1.1 to get user info
                response = requests.get(
                    'https://api.twitter.com/1.1/account/verify_credentials.json',
                    auth=auth
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.user_id = str(data.get('id'))
                    return self.user_id
                else:
                    logger.error(f"OAuth 1.0a failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"OAuth 1.0a error: {e}")
        
        # Fallback to Bearer Token
        if not self.bearer_token:
            logger.error("No authentication available")
            return None
            
        try:
            url = f"{self.base_url}/users/by/username/{self.username}"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    self.user_id = data['data']['id']
                    return self.user_id
                else:
                    logger.error(f"User not found: {data}")
                    return None
            else:
                logger.error(f"Failed to get user ID: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return None
    
    def is_configured(self) -> bool:
        """Check if service is properly configured"""
        return bool(self.consumer_key and self.consumer_secret and self.access_token and self.access_token_secret)
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get your Twitter account information"""
        try:
            # Use OAuth 1.0a to get real account info
            auth = self._get_oauth_auth()
            if not auth:
                return {"success": False, "error": "OAuth not configured"}
            
            # Get user info using API v1.1
            response = requests.get(
                'https://api.twitter.com/1.1/account/verify_credentials.json',
                auth=auth
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "account": {
                        "username": data.get('screen_name'),
                        "name": data.get('name'),
                        "user_id": str(data.get('id')),
                        "followers_count": data.get('followers_count', 0),
                        "following_count": data.get('friends_count', 0),
                        "tweet_count": data.get('statuses_count', 0),
                        "listed_count": data.get('listed_count', 0),
                        "verified": data.get('verified', False),
                        "description": data.get('description', ''),
                        "location": data.get('location', ''),
                        "created_at": data.get('created_at')
                    }
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}
                
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"success": False, "error": str(e)}
    
    def get_my_tweets(self, limit: int = 25) -> Dict[str, Any]:
        """Get your own tweets with public metrics using API v2 with rate limiting"""
        try:
            # Check cache first
            cache_key = f"tweets_{limit}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                logger.info("Returning cached tweet data")
                return cached_data
            
            # Check if we have last successful data to show as fallback
            if cache_key in self.last_successful_data:
                logger.info("Rate limited - returning last successful data as fallback")
                fallback_data = self.last_successful_data[cache_key].copy()
                fallback_data["message"] = "Showing last fetched data (rate limited)"
                fallback_data["cached"] = True
                return fallback_data
            
            # First get user ID using OAuth 1.0a
            auth = self._get_oauth_auth()
            if not auth:
                return {"success": False, "error": "OAuth not configured"}
            
            # Get user ID from OAuth 1.0a
            user_id = self._get_user_id()
            if not user_id:
                return {"success": False, "error": "Could not get user ID"}
            
            # Try API v2 with Bearer Token for tweet metrics (with rate limiting)
            if self.bearer_token:
                url = f"{self.base_url}/users/{user_id}/tweets"
                params = {
                    "tweet.fields": "public_metrics,created_at,conversation_id",
                    "max_results": max(5, min(limit, 100))  # API requires 5-100
                }
                
                response = self._make_request(url, params=params, headers=self._get_headers())
                
                if response.status_code == 200:
                    data = response.json()
                    tweets_data = data.get('data', [])
                    tweets = []
                    
                    for tweet in tweets_data:
                        metrics = tweet.get('public_metrics', {})
                        tweets.append({
                            "id": str(tweet.get('id')),
                            "text": tweet.get('text', ''),
                            "created_at": tweet.get('created_at'),
                            "conversation_id": str(tweet.get('conversation_id', tweet.get('id'))),
                            "like_count": metrics.get('like_count', 0),
                            "retweet_count": metrics.get('retweet_count', 0),
                            "reply_count": metrics.get('reply_count', 0),
                            "quote_count": metrics.get('quote_count', 0),
                            "bookmark_count": metrics.get('bookmark_count', 0),
                            "impression_count": metrics.get('impression_count', 0),
                            "url": f"https://twitter.com/{self.username}/status/{tweet.get('id')}"
                        })
                    
                    result = {
                        "success": True,
                        "tweets": tweets,
                        "total_tweets": len(tweets)
                    }
                    
                    # Cache the result and store as last successful data
                    self._cache_data(cache_key, result)
                    self.last_successful_data[cache_key] = result
                    return result
                    
                elif response.status_code == 403:
                    # Account is private or restricted
                    result = {
                        "success": True,
                        "tweets": [],
                        "total_tweets": 0,
                        "message": "Account is private - tweets not accessible via public API"
                    }
                    self._cache_data(cache_key, result)
                    self.last_successful_data[cache_key] = result
                    return result
                    
                elif response.status_code == 429:
                    # Rate limited - return last successful data if available
                    logger.warning("Rate limited - checking for last successful data")
                    if cache_key in self.last_successful_data:
                        fallback_data = self.last_successful_data[cache_key].copy()
                        fallback_data["message"] = "Showing last fetched data (rate limited)"
                        fallback_data["cached"] = True
                        return fallback_data
                    else:
                        return {
                            "success": True,
                            "tweets": [],
                            "total_tweets": 0,
                            "message": "Rate limited - no previous data available"
                        }
                else:
                    logger.warning(f"API v2 error {response.status_code}: {response.text}")
            
            # Fallback to OAuth 1.0a search API (only if Bearer Token fails)
            url = 'https://api.twitter.com/1.1/search/tweets.json'
            params = {
                'q': f'from:{self.username}',
                'count': min(limit, 100),  # API limit
                'result_type': 'recent'
            }
            
            response = requests.get(url, auth=auth, params=params)
            
            if response.status_code == 200:
                data = response.json()
                tweets_data = data.get('statuses', [])
                tweets = []
                
                for tweet in tweets_data:
                    tweets.append({
                        "id": str(tweet.get('id')),
                        "text": tweet.get('text', ''),
                        "created_at": tweet.get('created_at'),
                        "conversation_id": str(tweet.get('id')),
                        "like_count": tweet.get('favorite_count', 0),
                        "retweet_count": tweet.get('retweet_count', 0),
                        "reply_count": 0,  # Not available in v1.1
                        "quote_count": 0,  # Not available in v1.1
                        "bookmark_count": 0,  # Not available in v1.1
                        "impression_count": 0,  # Not available in free tier
                        "url": f"https://twitter.com/{self.username}/status/{tweet.get('id')}"
                    })
                
                result = {
                    "success": True,
                    "tweets": tweets,
                    "total_tweets": len(tweets)
                }
                self._cache_data(cache_key, result)
                self.last_successful_data[cache_key] = result
                return result
            else:
                # If both fail, return last successful data if available
                if cache_key in self.last_successful_data:
                    fallback_data = self.last_successful_data[cache_key].copy()
                    fallback_data["message"] = "Showing last fetched data (API unavailable)"
                    fallback_data["cached"] = True
                    return fallback_data
                else:
                    logger.warning(f"All API methods failed, returning empty tweets")
                    return {
                        "success": True,
                        "tweets": [],
                        "total_tweets": 0,
                        "message": "Tweets not accessible with current API access level"
                    }
                
        except Exception as e:
            logger.error(f"Error getting my tweets: {e}")
            return {"success": False, "error": str(e)}
    
    def get_tweet_replies(self, tweet_id: str, limit: int = 25) -> Dict[str, Any]:
        """Get replies to a specific tweet"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        try:
            url = f"{self.base_url}/tweets/search/recent"
            params = {
                "query": f"conversation_id:{tweet_id}",
                "tweet.fields": "author_id,created_at,public_metrics",
                "max_results": min(limit, 100)
            }
            
            response = requests.get(url, headers=self._get_headers(), params=params)
            
            if response.status_code == 200:
                data = response.json()
                replies = []
                
                for tweet in data.get('data', []):
                    # Skip the original tweet (same ID)
                    if tweet.get('id') == tweet_id:
                        continue
                        
                    metrics = tweet.get('public_metrics', {})
                    replies.append({
                        "id": tweet.get('id'),
                        "text": tweet.get('text', ''),
                        "author_id": tweet.get('author_id'),
                        "created_at": tweet.get('created_at'),
                        "like_count": metrics.get('like_count', 0),
                        "retweet_count": metrics.get('retweet_count', 0),
                        "reply_count": metrics.get('reply_count', 0),
                        "quote_count": metrics.get('quote_count', 0)
                    })
                
                return {
                    "success": True,
                    "replies": replies,
                    "total_replies": len(replies)
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting tweet replies: {e}")
            return {"success": False, "error": str(e)}
    
    def get_tweet_analytics(self, tweet_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific tweet"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        try:
            # Get tweet details
            url = f"{self.base_url}/tweets/{tweet_id}"
            params = {
                "tweet.fields": "public_metrics,created_at,conversation_id"
            }
            
            response = requests.get(url, headers=self._get_headers(), params=params)
            
            if response.status_code == 200:
                data = response.json()
                tweet_data = data.get('data', {})
                metrics = tweet_data.get('public_metrics', {})
                
                # Get replies for engagement analysis
                replies_data = self.get_tweet_replies(tweet_id, limit=100)
                replies = replies_data.get('replies', []) if replies_data.get('success') else []
                
                # Calculate engagement metrics
                like_count = metrics.get('like_count', 0)
                retweet_count = metrics.get('retweet_count', 0)
                reply_count = metrics.get('reply_count', 0)
                quote_count = metrics.get('quote_count', 0)
                impression_count = metrics.get('impression_count', 0)
                
                total_engagement = like_count + retweet_count + reply_count + quote_count
                engagement_rate = (total_engagement / impression_count * 100) if impression_count > 0 else 0
                
                # Calculate time metrics
                created_at = tweet_data.get('created_at')
                if created_at:
                    tweet_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    time_since_tweet = datetime.now(timezone.utc) - tweet_time
                else:
                    time_since_tweet = None
                
                analytics = {
                    "tweet_id": tweet_id,
                    "text": tweet_data.get('text', ''),
                    "created_at": created_at,
                    "time_since_tweet": str(time_since_tweet).split('.')[0] if time_since_tweet else None,
                    "metrics": {
                        "likes": like_count,
                        "retweets": retweet_count,
                        "replies": reply_count,
                        "quotes": quote_count,
                        "bookmarks": metrics.get('bookmark_count', 0),
                        "impressions": impression_count,
                        "total_engagement": total_engagement,
                        "engagement_rate": round(engagement_rate, 2)
                    },
                    "replies": {
                        "count": len(replies),
                        "recent_replies": replies[:5]  # Last 5 replies
                    },
                    "url": f"https://twitter.com/{self.username}/status/{tweet_id}"
                }
                
                return {"success": True, "analytics": analytics}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting tweet analytics: {e}")
            return {"success": False, "error": str(e)}
    
    def get_account_analytics(self) -> Dict[str, Any]:
        """Get comprehensive account analytics"""
        if not self.is_configured():
            return {"success": False, "error": "Service not configured"}
        
        try:
            # Get account info
            account_info = self.get_account_info()
            if not account_info.get("success"):
                return account_info
            
            # Get recent tweets
            tweets_data = self.get_my_tweets(limit=100)
            if not tweets_data.get("success"):
                return tweets_data
            
            tweets = tweets_data.get("tweets", [])
            
            # Calculate analytics
            total_tweets = len(tweets)
            
            # Tweet analytics
            total_likes = sum(tweet.get("like_count", 0) for tweet in tweets)
            total_retweets = sum(tweet.get("retweet_count", 0) for tweet in tweets)
            total_replies = sum(tweet.get("reply_count", 0) for tweet in tweets)
            total_quotes = sum(tweet.get("quote_count", 0) for tweet in tweets)
            total_impressions = sum(tweet.get("impression_count", 0) for tweet in tweets)
            
            avg_likes = total_likes / total_tweets if total_tweets > 0 else 0
            avg_retweets = total_retweets / total_tweets if total_tweets > 0 else 0
            avg_replies = total_replies / total_tweets if total_tweets > 0 else 0
            avg_impressions = total_impressions / total_tweets if total_tweets > 0 else 0
            
            # Engagement rate calculation
            total_engagement = total_likes + total_retweets + total_replies + total_quotes
            overall_engagement_rate = (total_engagement / total_impressions * 100) if total_impressions > 0 else 0
            
            # Top performing tweets
            top_tweets = sorted(tweets, key=lambda x: x.get("like_count", 0) + x.get("retweet_count", 0), reverse=True)[:5]
            
            # Recent activity (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_tweets = []
            for tweet in tweets:
                if tweet.get("created_at"):
                    tweet_time = datetime.fromisoformat(tweet["created_at"].replace('Z', '+00:00'))
                    if tweet_time > week_ago:
                        recent_tweets.append(tweet)
            
            analytics = {
                "account": account_info.get("account", {}),
                "summary": {
                    "total_tweets": total_tweets,
                    "total_likes": total_likes,
                    "total_retweets": total_retweets,
                    "total_replies": total_replies,
                    "total_quotes": total_quotes,
                    "total_impressions": total_impressions,
                    "avg_likes": round(avg_likes, 2),
                    "avg_retweets": round(avg_retweets, 2),
                    "avg_replies": round(avg_replies, 2),
                    "avg_impressions": round(avg_impressions, 2),
                    "overall_engagement_rate": round(overall_engagement_rate, 2),
                    "recent_tweets_7_days": len(recent_tweets)
                },
                "top_tweets": top_tweets,
                "recent_activity": {
                    "tweets": recent_tweets[:10]
                }
            }
            
            return {"success": True, "analytics": analytics}
            
        except Exception as e:
            logger.error(f"Error getting account analytics: {e}")
            return {"success": False, "error": str(e)}

# Global service instance
twitter_analytics_service = TwitterAnalyticsService()
