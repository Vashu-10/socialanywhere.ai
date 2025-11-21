"""
Authentication service for Google OAuth integration
Handles user authentication, session management, and user data operations
"""

import os
import uuid
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from database import db_manager
from models import User, UserResponse


class AuthService:
    """Service class for authentication operations"""
    
    def __init__(self):
        self.google_client_id = "864294913881-4fk0t2hpk8mgc5b5ai7ck85mlsebhqto.apps.googleusercontent.com"
        self.jwt_secret = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24 * 7  # 7 days
    
    async def verify_google_token(self, token: str) -> Dict[str, Any]:
        """Verify Google OAuth token and extract user information"""
        try:
            print(f"🔍 Verifying Google token with client_id: {self.google_client_id}")
            print(f"🔍 Token length: {len(token)}")
            
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                self.google_client_id
            )
            
            print(f"✅ Token verified successfully for user: {idinfo.get('email')}")
            
            # Extract user information
            user_info = {
                "google_id": idinfo["sub"],
                "email": idinfo["email"],
                "name": idinfo["name"],
                "picture_url": idinfo.get("picture"),
                "email_verified": idinfo.get("email_verified", False)
            }
            
            print(f"📋 User info extracted: {user_info}")
            return user_info
            
        except ValueError as e:
            print(f"❌ Google token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google token: {str(e)}"
            )
        except Exception as e:
            print(f"❌ Unexpected error during token verification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication error: {str(e)}"
            )
    
    async def get_or_create_user(self, user_info: Dict[str, Any]) -> User:
        """Get existing user or create new user from Google info"""
        try:
            # Check if user exists by Google ID
            query = "SELECT * FROM users WHERE google_id = :google_id"
            existing_user = await db_manager.fetch_one(query, {"google_id": user_info["google_id"]})
            
            if existing_user:
                # Update user info if needed
                user = User(
                    id=existing_user["id"],
                    google_id=existing_user["google_id"],
                    email=existing_user["email"],
                    name=existing_user["name"],
                    picture_url=existing_user["picture_url"],
                    is_active=existing_user["is_active"],
                    created_at=existing_user["created_at"],
                    updated_at=existing_user["updated_at"]
                )
                
                # Update user info if it has changed
                if (user.name != user_info["name"] or 
                    user.picture_url != user_info["picture_url"]):
                    
                    update_query = """
                        UPDATE users 
                        SET name = :name, picture_url = :picture_url, updated_at = NOW()
                        WHERE google_id = :google_id
                    """
                    await db_manager.execute_query(update_query, {
                        "name": user_info["name"],
                        "picture_url": user_info["picture_url"],
                        "google_id": user_info["google_id"]
                    })
                
                return user
            else:
                # Create new user
                user_id = str(uuid.uuid4())
                insert_query = """
                    INSERT INTO users (id, google_id, email, name, picture_url, is_active)
                    VALUES (:id, :google_id, :email, :name, :picture_url, :is_active)
                """
                
                await db_manager.execute_query(insert_query, {
                    "id": user_id,
                    "google_id": user_info["google_id"],
                    "email": user_info["email"],
                    "name": user_info["name"],
                    "picture_url": user_info["picture_url"],
                    "is_active": True
                })
                
                # Fetch the created user
                query = "SELECT * FROM users WHERE id = :id"
                new_user = await db_manager.fetch_one(query, {"id": user_id})
                
                return User(
                    id=new_user["id"],
                    google_id=new_user["google_id"],
                    email=new_user["email"],
                    name=new_user["name"],
                    picture_url=new_user["picture_url"],
                    is_active=new_user["is_active"],
                    created_at=new_user["created_at"],
                    updated_at=new_user["updated_at"]
                )
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error managing user: {str(e)}"
            )
    
    def create_access_token(self, user_id: str) -> str:
        """Create JWT token for user session"""
        payload = {
            "user_id": str(user_id),
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        try:
            # Removed verbose logging for successful token verifications to reduce log spam
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError as e:
            print(f"❌ JWT token expired: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            print(f"❌ Invalid JWT token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            print(f"❌ Unexpected JWT error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            )
    
    async def get_current_user(self, token: str) -> User:
        """Get current user from JWT token"""
        try:
            # Verify the JWT token (logging reduced to prevent spam)
            payload = self.verify_jwt_token(token)
            user_id = payload.get("user_id")
            
            if not user_id:
                print("❌ No user_id in token payload")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # Get user from database
            user = await self.get_user_by_id(user_id)
            if not user:
                print(f"❌ User not found in database for user_id: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Only log successful user lookups every 100th time to reduce spam
            # while still providing some visibility into system activity
            import random
            if random.randint(1, 100) == 1:
                print(f"✅ User authenticated: {user.email}")
            
            return user
            
        except HTTPException as e:
            print(f"❌ HTTP Exception in get_current_user: {e.detail}")
            raise e
        except Exception as e:
            print(f"❌ Unexpected error in get_current_user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            query = "SELECT * FROM users WHERE id = :user_id AND is_active = true"
            user_data = await db_manager.fetch_one(query, {"user_id": user_id})
            
            if user_data:
                return User(
                    id=user_data["id"],
                    google_id=user_data["google_id"],
                    email=user_data["email"],
                    name=user_data["name"],
                    picture_url=user_data["picture_url"],
                    is_active=user_data["is_active"],
                    created_at=user_data["created_at"],
                    updated_at=user_data["updated_at"]
                )
            return None
            
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    async def get_user_by_token(self, token: str) -> Optional[User]:
        """Get user from JWT token"""
        try:
            payload = self.verify_jwt_token(token)
            user_id = payload.get("user_id")
            
            if user_id:
                return await self.get_user_by_id(user_id)
            return None
            
        except HTTPException:
            return None
        except Exception as e:
            print(f"Error getting user by token: {e}")
            return None
    
    async def delete_user_account(self, user_id: str) -> bool:
        """Delete user account and all associated data"""
        try:
            # Delete all user-related data in the correct order (respecting foreign key constraints)
            
            # 1. Delete calendar events
            await db_manager.execute_query(
                "DELETE FROM calendar_events WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            
            # 2. Delete batch operations
            await db_manager.execute_query(
                "DELETE FROM batch_operations WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            
            # 3. Delete posting schedules (via posts)
            await db_manager.execute_query(
                "DELETE FROM posting_schedules WHERE post_id IN (SELECT id FROM posts WHERE user_id = :user_id)",
                {"user_id": user_id}
            )
            
            # 4. Delete captions (via posts)
            await db_manager.execute_query(
                "DELETE FROM captions WHERE post_id IN (SELECT id FROM posts WHERE user_id = :user_id)",
                {"user_id": user_id}
            )
            
            # 5. Delete images (via posts)
            await db_manager.execute_query(
                "DELETE FROM images WHERE post_id IN (SELECT id FROM posts WHERE user_id = :user_id)",
                {"user_id": user_id}
            )
            
            # 6. Delete posts
            await db_manager.execute_query(
                "DELETE FROM posts WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            
            # 7. Delete campaigns
            await db_manager.execute_query(
                "DELETE FROM campaigns WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            
            # 8. Finally, delete the user
            await db_manager.execute_query(
                "DELETE FROM users WHERE id = :user_id",
                {"user_id": user_id}
            )
            
            print(f"Successfully deleted user account: {user_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting user account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user account: {str(e)}"
            )


# Global auth service instance
auth_service = AuthService()
