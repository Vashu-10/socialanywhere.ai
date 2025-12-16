from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import os
import json
import io
import time
import requests
from PIL import Image

router = APIRouter()

# This is the file that will store the user's access and refresh tokens.
# It is created automatically when the authorization flow completes for the first
# time.
TOKEN_FILE = 'token.json'
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 
          'https://www.googleapis.com/auth/drive', 
          'https://www.googleapis.com/auth/analytics.readonly', 
          'https://mail.google.com/',
          'https://www.googleapis.com/auth/calendar']

def get_google_flow():
    if not os.path.exists('Credentials.json'):
        print("Credentials.json not found!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credentials.json not found. Please create it with your Google Cloud credentials."
        )
    # Allow configuring redirect URI to avoid redirect_uri_mismatch
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/callback')
    print(f"Using Google OAuth redirect URI: {redirect_uri}")
    flow = Flow.from_client_secrets_file(
        'Credentials.json',
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return flow

@router.get("/google/connect")
async def connect_google(flow: Flow = Depends(get_google_flow)):
    print("Connecting to Google...")
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    print(f"Redirecting to: {authorization_url}")
    return RedirectResponse(authorization_url)

@router.get("/callback")
async def google_callback(code: str, flow: Flow = Depends(get_google_flow)):
    print("Received callback from Google.")
    print(f"Code: {code}")
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Ensure no corrupted token file exists before writing
        if os.path.exists(TOKEN_FILE):
            if os.path.isdir(TOKEN_FILE):
                print(f"Removing corrupted token directory: {TOKEN_FILE}")
                import shutil
                try:
                    shutil.rmtree(TOKEN_FILE)
                except Exception as e:
                    # Try to rename if removal fails
                    backup_name = f"{TOKEN_FILE}_old_{int(time.time())}"
                    try:
                        os.rename(TOKEN_FILE, backup_name)
                        print(f"Renamed corrupted directory to: {backup_name}")
                    except Exception as rename_error:
                        print(f"Failed to clean up corrupted token file: {rename_error}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Cannot clean up corrupted token file. Please check file permissions."
                        )
        
        # Write token with robust, cross-platform-safe logic
        temp_token_file = f"{TOKEN_FILE}.tmp"
        try:
            # Ensure parent directory exists
            token_dir = os.path.dirname(TOKEN_FILE) or "."
            os.makedirs(token_dir, exist_ok=True)

            # Write to temp file first
            with open(temp_token_file, 'w') as token:
                token.write(credentials.to_json())
                token.flush()  # Ensure data is written
                os.fsync(token.fileno())  # Force write to disk

            # Try to move temp -> final, handling EBUSY on some host/volume setups
            last_error = None
            for attempt in range(5):
                try:
                    # Remove existing token file/dir if present
                    if os.path.exists(TOKEN_FILE):
                        if os.path.isdir(TOKEN_FILE):
                            import shutil
                            shutil.rmtree(TOKEN_FILE)
                        else:
                            os.remove(TOKEN_FILE)
                    # Prefer atomic replace
                    try:
                        os.replace(temp_token_file, TOKEN_FILE)
                    except Exception:
                        # Fallback to move if replace not available
                        import shutil
                        shutil.move(temp_token_file, TOKEN_FILE)
                    print("Successfully fetched and stored token.")
                    last_error = None
                    break
                except Exception as e:
                    last_error = e
                    print(f"Warning: failed to finalize token file (attempt {attempt+1}/5): {e}")
                    time.sleep(0.3 * (attempt + 1))

            if last_error is not None:
                # If still failing, raise detailed error
                raise last_error

        except Exception as write_error:
            # Clean up temp file if write failed
            try:
                if os.path.exists(temp_token_file):
                    os.remove(temp_token_file)
            except Exception:
                pass
            raise write_error
            
    except Exception as e:
        print(f"Error fetching token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching token: {e}"
        )
    return RedirectResponse(url="http://localhost:8000/settings")

@router.get("/google/status")
async def get_google_status():
    """Report whether Google is actually connected.
    We validate token.json contents (must be a file with a refresh_token),
    not just existence, to avoid false positives.
    """
    try:
        if not os.path.exists(TOKEN_FILE):
            return {"connected": False}
        if os.path.isdir(TOKEN_FILE):
            # Corrupted state: a directory where a file should be
            return {"connected": False, "error": "token_is_directory"}
        # Try to parse token and check refresh_token
        with open(TOKEN_FILE, "r") as f:
            raw = f.read().strip() or "{}"
            data = json.loads(raw)
        has_refresh = bool(data.get("refresh_token"))
        return {"connected": has_refresh}
    except Exception as e:
        # Any error -> treat as not connected
        return {"connected": False, "error": str(e)}

@router.post("/google/disconnect")
async def disconnect_google():
    """Remove token.json to fully disconnect Google account."""
    try:
        if os.path.exists(TOKEN_FILE):
            if os.path.isdir(TOKEN_FILE):
                import shutil
                shutil.rmtree(TOKEN_FILE)
            else:
                os.remove(TOKEN_FILE)
        return {"success": True, "message": "Disconnected from Google"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {e}")

def get_google_service(service_name: str, version: str):
    creds = None
    if os.path.exists(TOKEN_FILE):
        # Enhanced token file corruption handling
        try:
            # Check if TOKEN_FILE is a directory instead of a file
            if os.path.isdir(TOKEN_FILE):
                print(f"Warning: {TOKEN_FILE} is a directory, not a file. Attempting to remove it.")
                import shutil
                try:
                    shutil.rmtree(TOKEN_FILE)
                    print(f"Successfully removed corrupted directory: {TOKEN_FILE}")
                except PermissionError as e:
                    print(f"Permission error removing directory {TOKEN_FILE}: {e}")
                    # Try to rename it instead of removing
                    backup_name = f"{TOKEN_FILE}_corrupted_{int(time.time())}"
                    try:
                        os.rename(TOKEN_FILE, backup_name)
                        print(f"Renamed corrupted directory to: {backup_name}")
                    except Exception as rename_error:
                        print(f"Failed to rename corrupted directory: {rename_error}")
                except Exception as e:
                    print(f"Error removing corrupted token directory: {e}")
                    # Try alternative cleanup method
                    backup_name = f"{TOKEN_FILE}_corrupted_{int(time.time())}"
                    try:
                        os.rename(TOKEN_FILE, backup_name)
                        print(f"Renamed corrupted directory to: {backup_name}")
                    except Exception as rename_error:
                        print(f"Failed to rename corrupted directory: {rename_error}")
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google token file was corrupted and has been cleaned up. Please reconnect your account."
                )
            
            # Check if file is readable
            if not os.access(TOKEN_FILE, os.R_OK):
                print(f"Warning: {TOKEN_FILE} is not readable")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google token file is not readable. Please reconnect your account."
                )
            
            # Try to load credentials
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except json.JSONDecodeError as e:
                print(f"Warning: {TOKEN_FILE} contains invalid JSON: {e}")
                # Move corrupted file and create fresh one
                backup_name = f"{TOKEN_FILE}_corrupted_{int(time.time())}"
                try:
                    os.rename(TOKEN_FILE, backup_name)
                    print(f"Renamed corrupted token file to: {backup_name}")
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google token file is corrupted (invalid JSON). Please reconnect your account."
                )
            except Exception as e:
                print(f"Warning: Failed to load token file {TOKEN_FILE}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to load Google token file: {str(e)}. Please reconnect your account."
                )
            
            if not creds.refresh_token:
                print(f"Warning: {TOKEN_FILE} missing refresh token")
                try:
                    os.remove(TOKEN_FILE)
                except Exception as e:
                    print(f"Failed to remove token file: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing refresh token. Please reconnect your account."
                )
                
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            print(f"Unexpected error handling token file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error with Google token file: {str(e)}"
            )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorized with Google. Please connect your account."
            )
    return build(service_name, version, credentials=creds)

class Activity(BaseModel):
    time: int
    text: str

class Campaign(BaseModel):
    id: str
    productDescription: str
    generatedContent: str
    scheduledAt: Optional[str]
    status: str
    imageUrl: Optional[str]
    driveImageUrl: Optional[str] = None
    activity: List[Activity]

@router.post("/google-drive/save-campaign")
async def save_campaign_to_drive(campaign: Campaign, drive_service = Depends(lambda: get_google_service('drive', 'v3'))):
    print("Saving campaign to drive...")
    try:
        image_file_id = None
        if campaign.imageUrl:
            print("Uploading image to Google Drive...")
            
            # Handle local vs remote image URLs
            try:
                if campaign.imageUrl.startswith('/public/'):
                    # Local file path
                    local_path = campaign.imageUrl.replace('/public/', 'public/')
                    print(f"Reading local image file: {local_path}")
                    
                    if not os.path.exists(local_path):
                        raise FileNotFoundError(f"Local image file not found: {local_path}")
                    
                    image = Image.open(local_path)
                elif campaign.imageUrl.startswith('http://localhost:') or campaign.imageUrl.startswith('http://127.0.0.1:'):
                    # Local server URL - convert to file path
                    # Extract the filename from the URL, should work for both placeholder and generated images
                    filename = campaign.imageUrl.split('/')[-1]
                    local_path = f'public/{filename}'
                    print(f"Converting localhost URL to local path: {local_path}")
                    
                    if not os.path.exists(local_path):
                        raise FileNotFoundError(f"Local image file not found: {local_path}")
                    
                    image = Image.open(local_path)
                else:
                    # Remote URL - download with timeout
                    print(f"Downloading remote image: {campaign.imageUrl}")
                    response = requests.get(campaign.imageUrl, stream=True, timeout=30)
                    response.raise_for_status()
                    image = Image.open(response.raw)
                
                print("Converting image to JPEG...")
                
                # Resize image if too large to prevent hanging
                max_size = (1920, 1920)
                if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                    image.thumbnail(max_size, Image.Resampling.LANCZOS)
                    print(f"Resized image to {image.size}")
                
                # Convert to RGB if necessary
                if image.mode in ('RGBA', 'P'):
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = rgb_image
                
                jpeg_image = io.BytesIO()
                image.save(jpeg_image, 'JPEG', quality=85, optimize=True)
                jpeg_image.seek(0)
                
                print(f"Image processed, size: {len(jpeg_image.getvalue())} bytes")

                image_file_metadata = {
                    'name': f'campaign_{campaign.id}_image.jpeg',
                    'mimeType': 'image/jpeg'
                }
                
                # Use simple upload for smaller files (< 5MB), resumable for larger
                file_size = len(jpeg_image.getvalue())
                resumable = file_size > 5 * 1024 * 1024  # 5MB threshold
                media = MediaIoBaseUpload(jpeg_image, mimetype='image/jpeg', resumable=resumable)
                
                print(f"Creating image file in Google Drive (resumable: {resumable})...")
                
                # Create with timeout handling
                request = drive_service.files().create(
                    body=image_file_metadata,
                    media_body=media,
                    fields='id'
                )
                
                if resumable:
                    # Handle resumable upload with retries
                    response = None
                    retry_count = 0
                    max_retries = 3
                    
                    while response is None and retry_count < max_retries:
                        try:
                            status, response = request.next_chunk()
                            if status:
                                print(f"Upload progress: {int(status.progress() * 100)}%")
                        except Exception as chunk_error:
                            retry_count += 1
                            print(f"Upload chunk failed (attempt {retry_count}): {chunk_error}")
                            if retry_count >= max_retries:
                                raise chunk_error
                    
                    image_file = response
                else:
                    # Simple upload
                    image_file = request.execute()
                
                image_file_id = image_file.get('id')
                print(f"Image uploaded with ID: {image_file_id}")
                
            except requests.exceptions.Timeout:
                print("Image download timed out, continuing without image...")
                image_file_id = None
            except requests.exceptions.RequestException as req_error:
                print(f"Image download failed: {req_error}, continuing without image...")
                image_file_id = None
            except Exception as img_error:
                print(f"Image processing/upload failed: {img_error}, continuing without image...")
                image_file_id = None

        print("Creating campaign JSON file...")
        file_metadata = {
            'name': f'campaign_{campaign.id}_{datetime.now().isoformat().replace(":", "-")}.json',
            'mimeType': 'application/json'
        }
        campaign_data = campaign.dict()
        campaign_data['createdAt'] = datetime.now().isoformat()
        if image_file_id:
            # Store Google Drive URL in JSON file for backup/sharing
            # Use the correct direct image URL format
            campaign_data['driveImageUrl'] = f"https://drive.google.com/file/d/{image_file_id}/view"
            campaign_data['imageFileId'] = image_file_id
            # Keep original localhost URL for UI display

        file_content = json.dumps(campaign_data, indent=2).encode('utf-8')
        
        # Use simple upload for JSON files (they're typically small)
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/json', resumable=False)

        print("Creating JSON file in Google Drive...")
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"JSON file created with ID: {file.get('id')}")
        
        # Return updated campaign data including the Google Drive image URL
        response_data = {
            "success": True, 
            "fileId": file.get('id'), 
            "imageFileId": image_file_id
        }
        
        # Include Drive image info in response if image was uploaded
        # But don't update the imageUrl - keep localhost URL for UI display
        if image_file_id:
            response_data["driveImageUrl"] = f"https://drive.google.com/file/d/{image_file_id}/view"
            response_data["updatedCampaignData"] = campaign_data
        
        print(f"Returning response: {response_data}")
        return response_data
    except Exception as e:
        print(f"Error saving campaign to drive: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving campaign to drive: {e}"
        )

@router.post("/google-calendar/create-event")
async def create_calendar_event(campaign: Campaign, calendar_service = Depends(lambda: get_google_service('calendar', 'v3'))):
    print("Creating calendar event...")
    if not campaign.scheduledAt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign must have a scheduled date to create a calendar event."
        )

    try:
        # Parse the scheduled time
        start_time = datetime.fromisoformat(campaign.scheduledAt.replace('Z', '+00:00'))
        end_time = start_time + timedelta(minutes=30)
        
        # Create a more detailed event description
        description_parts = [
            f"📱 Social Media Post Reminder",
            f"📝 Content: {campaign.generatedContent[:100]}{'...' if len(campaign.generatedContent) > 100 else ''}",
            f"🎯 Product: {campaign.productDescription}",
            f"📊 Status: {campaign.status}"
        ]
        
        # Use Google Drive URL if available, otherwise use local URL
        image_url_for_calendar = getattr(campaign, 'driveImageUrl', None) or campaign.imageUrl
        if image_url_for_calendar:
            description_parts.append(f"🖼️ Image: {image_url_for_calendar}")
        
        event = {
            'summary': f"📱 Post: {campaign.productDescription[:50]}{'...' if len(campaign.productDescription) > 50 else ''}",
            'description': '\n'.join(description_parts),
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},
                    {'method': 'email', 'minutes': 60},
                ],
            },
            'colorId': '2',  # Green color for social media posts
        }

        created_event = calendar_service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {created_event.get('htmlLink')}")
        
        return {
            "success": True, 
            "eventLink": created_event.get('htmlLink'),
            "eventId": created_event.get('id'),
            "summary": created_event.get('summary')
        }
        
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating calendar event: {e}"
        )

class BatchCalendarRequest(BaseModel):
    campaigns: List[Campaign]

@router.post("/google-calendar/create-batch-events")
async def create_batch_calendar_events(request: BatchCalendarRequest, calendar_service = Depends(lambda: get_google_service('calendar', 'v3'))):
    print(f"Creating batch calendar events for {len(request.campaigns)} campaigns...")
    
    if not request.campaigns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No campaigns provided for batch event creation."
        )
    
    results = []
    success_count = 0
    
    for campaign in request.campaigns:
        try:
            if not campaign.scheduledAt:
                results.append({
                    "campaignId": campaign.id,
                    "success": False,
                    "error": "Campaign must have a scheduled date"
                })
                continue
            
            # Parse the scheduled time
            start_time = datetime.fromisoformat(campaign.scheduledAt.replace('Z', '+00:00'))
            end_time = start_time + timedelta(minutes=30)
            
            # Create event description
            description_parts = [
                f"📱 Social Media Post Reminder",
                f"📝 Content: {campaign.generatedContent[:100]}{'...' if len(campaign.generatedContent) > 100 else ''}",
                f"🎯 Product: {campaign.productDescription}",
                f"📊 Status: {campaign.status}"
            ]
            
            # Use Google Drive URL if available, otherwise use local URL
            image_url_for_calendar = getattr(campaign, 'driveImageUrl', None) or campaign.imageUrl
            if image_url_for_calendar:
                description_parts.append(f"🖼️ Image: {image_url_for_calendar}")
            
            event = {
                'summary': f"📱 Post: {campaign.productDescription[:50]}{'...' if len(campaign.productDescription) > 50 else ''}",
                'description': '\n'.join(description_parts),
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 10},
                        {'method': 'email', 'minutes': 60},
                    ],
                },
                'colorId': '2',  # Green color for social media posts
            }

            created_event = calendar_service.events().insert(calendarId='primary', body=event).execute()
            
            results.append({
                "campaignId": campaign.id,
                "success": True,
                "eventLink": created_event.get('htmlLink'),
                "eventId": created_event.get('id'),
                "summary": created_event.get('summary')
            })
            success_count += 1
            
        except Exception as e:
            print(f"Error creating calendar event for campaign {campaign.id}: {e}")
            results.append({
                "campaignId": campaign.id,
                "success": False,
                "error": str(e)
            })
    
    print(f"Batch calendar events created: {success_count}/{len(request.campaigns)} successful")
    
    return {
        "success": success_count > 0,
        "total": len(request.campaigns),
        "successful": success_count,
        "failed": len(request.campaigns) - success_count,
        "results": results
    }

@router.get("/google-calendar/upcoming-events")
async def get_upcoming_events(calendar_service = Depends(lambda: get_google_service('calendar', 'v3'))):
    """Get upcoming calendar events for the next 30 days"""
    try:
        now = datetime.utcnow()
        time_max = now + timedelta(days=30)
        
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            timeMax=time_max.isoformat() + 'Z',
            maxResults=50,
            singleEvents=True,
            orderBy='startTime',
            q='📱 Post:'  # Filter for social media posts
        ).execute()
        
        events = events_result.get('items', [])
        
        return {
            "success": True,
            "events": [
                {
                    "id": event.get('id'),
                    "summary": event.get('summary'),
                    "start": event.get('start', {}).get('dateTime'),
                    "description": event.get('description'),
                    "htmlLink": event.get('htmlLink')
                }
                for event in events
            ],
            "total": len(events)
        }
        
    except Exception as e:
        print(f"Error fetching upcoming events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching upcoming events: {e}"
        )
