"""
Authentication routes for Google OAuth integration
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from auth_service import AuthService
from models import UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
auth_service = AuthService()


class GoogleTokenRequest(BaseModel):
    token: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/google", response_model=AuthResponse)
async def google_auth(request: GoogleTokenRequest):
    """
    Authenticate user with Google OAuth token
    """
    try:
        print(f"🚀 Google auth request received for token: {request.token[:50]}...")
        
        # Verify Google token and get user info
        user_info = await auth_service.verify_google_token(request.token)
        
        # Create or get user from database
        user = await auth_service.get_or_create_user(user_info)
        
        # Generate JWT token
        access_token = auth_service.create_access_token(user.id)
        
        print(f"✅ Authentication successful for user: {user.email}")
        
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.from_orm(user)
        )
        
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current authenticated user
    """
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return UserResponse.from_orm(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


@router.post("/logout")
async def logout():
    """
    Logout user (client-side token removal)
    """
    return {"message": "Successfully logged out"}


@router.delete("/delete-account")
async def delete_account(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Delete user account and all associated data
    """
    try:
        print(f"🔍 Delete account request received for token: {credentials.credentials[:50]}...")
        
        # Get current user
        user = await auth_service.get_current_user(credentials.credentials)
        print(f"✅ User found for deletion: {user.email}")
        
        # Delete user and all associated data
        await auth_service.delete_user_account(str(user.id))
        
        print(f"✅ Account deleted successfully for user: {user.email}")
        return {"message": "Account deleted successfully"}
        
    except HTTPException as e:
        print(f"❌ HTTP Exception in delete account: {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ Unexpected error in delete account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )


# Dependency to get current user in other routes
async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current user for protected routes"""
    return await auth_service.get_current_user(credentials.credentials)
