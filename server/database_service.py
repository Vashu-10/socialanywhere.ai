"""
Database service functions for Social Media Agent
Provides CRUD operations and business logic for database models
Dashboard statistics functionality for monitoring post metrics
"""
import os
import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from PIL import Image as PILImage
from database import db_manager, get_sync_db
from models import (
    Campaign, Post, Image, Caption, PostingSchedule, BatchOperation,
    PostResponse, CampaignResponse, ImageResponse, CaptionResponse,
    PostingScheduleResponse, BatchOperationResponse
)


class DatabaseService:
    """Service class for database operations"""
    
    @staticmethod
    async def get_dashboard_statistics(user_id: str = None) -> Dict[str, Any]:
        """Get dashboard statistics for a user
        
        Args:
            user_id: The user ID to get statistics for
            
        Returns:
            Dictionary with dashboard statistics
        """
        async with db_manager.get_async_session() as session:
            # Get total campaigns count
            total_campaigns_query = """
                SELECT COUNT(DISTINCT COALESCE(campaign_id, batch_id)) as total
                FROM posts
                WHERE user_id = $1
            """
            total_campaigns_result = await session.fetch_one(total_campaigns_query, user_id)
            total_campaigns = total_campaigns_result['total'] if total_campaigns_result else 0
            
            # Get posts this week count
            current_date = datetime.now()
            start_of_week = current_date - timedelta(days=current_date.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            
            posts_this_week_query = """
                SELECT COUNT(*) as total
                FROM posts
                WHERE user_id = $1
                AND created_at >= $2
            """
            posts_this_week_result = await session.fetch_one(posts_this_week_query, user_id, start_of_week)
            posts_this_week = posts_this_week_result['total'] if posts_this_week_result else 0
            
            # Get active campaigns count (with scheduled or published posts)
            active_campaigns_query = """
                SELECT COUNT(DISTINCT COALESCE(campaign_id, batch_id)) as total
                FROM posts
                WHERE user_id = $1
                AND status IN ('scheduled', 'published')
            """
            active_campaigns_result = await session.fetch_one(active_campaigns_query, user_id)
            active_campaigns = active_campaigns_result['total'] if active_campaigns_result else 0
            
            return {
                "total_campaigns": total_campaigns,
                "posts_this_week": posts_this_week,
                "active_campaigns": active_campaigns
            }
    
    @staticmethod
    async def create_post(
        campaign_name: str = None,
        original_description: str = None,
        caption: str = None,
        image_path: str = None,
        scheduled_at: datetime = None,
        campaign_id: str = None,
        platforms: List[str] = None,
        subreddit: str = None,
        status: str = None,
        batch_id: str = None,
        user_id: str = None
    ) -> str:
        """Create a new post and return its ID"""
        try:
            # Truncate caption if it's too long (database constraint workaround)
            if caption and len(caption) > 500:
                caption = caption[:497] + "..."
                # Caption truncated to 500 characters
            
            # Insert post with campaign_name (will work if column exists, ignore if not)
            try:
                # Try with campaign_name and user_id first
                query = """
                    INSERT INTO posts (id, user_id, campaign_id, campaign_name, original_description, caption, 
                                     image_path, scheduled_at, platforms, subreddit, status, batch_id)
                    VALUES (:id, :user_id, :campaign_id, :campaign_name, :description, :caption, :image_path, 
                           :scheduled_at, :platforms, :subreddit, :status, :batch_id)
                    RETURNING id
                """
                post_id = str(uuid.uuid4())
                values = {
                    "id": post_id,
                    "user_id": user_id,
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name or "",
                    "description": original_description,
                    "caption": caption,
                    "image_path": image_path,
                    "scheduled_at": scheduled_at,
                    "platforms": platforms,
                    "subreddit": subreddit,
                    "status": status or ("draft" if not scheduled_at else "scheduled"),
                    "batch_id": batch_id
                }
                await db_manager.execute_query(query, values)
                
                # Create calendar event if post is scheduled
                if scheduled_at and user_id:
                    await DatabaseService.create_calendar_event(
                        post_id=post_id,
                        user_id=user_id,
                        title=campaign_name or "Scheduled Post",
                        description=caption or original_description or "",
                        start_time=scheduled_at,
                        end_time=scheduled_at,
                        status="scheduled",
                        platforms=platforms or []
                    )
                
                return post_id
            except Exception as e:
                if "campaign_name" in str(e):
                    # Fallback to without campaign_name but with user_id
                    # Campaign name column not found, using fallback
                    query = """
                        INSERT INTO posts (id, user_id, campaign_id, original_description, caption, 
                                         image_path, scheduled_at, platforms, subreddit, status, batch_id)
                        VALUES (:id, :user_id, :campaign_id, :description, :caption, :image_path, 
                               :scheduled_at, :platforms, :subreddit, :status, :batch_id)
                        RETURNING id
                    """
                    post_id = str(uuid.uuid4())
                    values = {
                        "id": post_id,
                        "user_id": user_id,
                        "campaign_id": campaign_id,
                        "description": original_description,
                        "caption": caption,
                        "image_path": image_path,
                        "scheduled_at": scheduled_at,
                        "platforms": platforms,
                        "subreddit": subreddit,
                        "status": status or ("draft" if not scheduled_at else "scheduled"),
                        "batch_id": batch_id
                    }
                    await db_manager.execute_query(query, values)
                    
                    # Create calendar event if post is scheduled
                    if scheduled_at and user_id:
                        await DatabaseService.create_calendar_event(
                            post_id=post_id,
                            user_id=user_id,
                            title=campaign_name or "Scheduled Post",
                            description=caption or original_description or "",
                            start_time=scheduled_at,
                            end_time=scheduled_at,
                            status="scheduled",
                            platforms=platforms or []
                        )
                    
                    return post_id
                else:
                    raise e
            
        except Exception as e:
            print(f"Error creating post: {e}")
            raise
    
    @staticmethod
    async def save_image_info(
        post_id: str,
        file_path: str,
        generation_method: str,
        generation_prompt: str = None,
        generation_settings: Dict[str, Any] = None
    ) -> str:
        """Save image information to database"""
        try:
            # Extract file info
            file_name = os.path.basename(file_path)
            file_size = None
            image_width = None
            image_height = None
            mime_type = None
            
            # Get file stats if file exists
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                try:
                    with PILImage.open(file_path) as img:
                        image_width, image_height = img.size
                        mime_type = f"image/{img.format.lower()}" if img.format else None
                except Exception as e:
                    print(f"Could not read image dimensions: {e}")
            
            # Insert image record
            query = """
                INSERT INTO images (id, post_id, file_path, file_name, file_size,
                                  image_width, image_height, mime_type, generation_method,
                                  generation_prompt, generation_settings)
                VALUES (:id, :post_id, :file_path, :file_name, :file_size,
                       :image_width, :image_height, :mime_type, :generation_method,
                       :generation_prompt, :generation_settings)
                RETURNING id
            """
            
            image_id = str(uuid.uuid4())
            values = {
                "id": image_id,
                "post_id": post_id,
                "file_path": file_path,
                "file_name": file_name,
                "file_size": file_size,
                "image_width": image_width,
                "image_height": image_height,
                "mime_type": mime_type,
                "generation_method": generation_method,
                "generation_prompt": generation_prompt,
                "generation_settings": generation_settings
            }
            
            await db_manager.execute_query(query, values)
            return image_id
            
        except Exception as e:
            print(f"Error saving image info: {e}")
            raise
    
    @staticmethod
    async def save_caption_info(
        post_id: str,
        content: str,
        generation_method: str = "groq",
        generation_prompt: str = None,
        language: str = "en"
    ) -> str:
        """Save caption information to database"""
        try:
            # Extract hashtags from caption
            hashtags = re.findall(r'#\w+', content)
            word_count = len(content.split())
            
            query = """
                INSERT INTO captions (id, post_id, content, generation_method,
                                    generation_prompt, language, hashtags, word_count)
                VALUES (:id, :post_id, :content, :generation_method,
                       :generation_prompt, :language, :hashtags, :word_count)
                RETURNING id
            """
            
            caption_id = str(uuid.uuid4())
            values = {
                "id": caption_id,
                "post_id": post_id,
                "content": content,
                "generation_method": generation_method,
                "generation_prompt": generation_prompt,
                "language": language,
                "hashtags": hashtags,
                "word_count": word_count
            }
            
            await db_manager.execute_query(query, values)
            return caption_id
            
        except Exception as e:
            print(f"Error saving caption info: {e}")
            raise
    
    @staticmethod
    async def save_posting_schedule(
        post_id: str,
        scheduled_at: datetime,
        time_zone: str = "UTC",
        priority: int = 1,
        auto_post: bool = False
    ) -> str:
        """Save posting schedule information"""
        try:
            query = """
                INSERT INTO posting_schedules (id, post_id, scheduled_at, time_zone,
                                             priority, auto_post, status)
                VALUES (:id, :post_id, :scheduled_at, :time_zone,
                       :priority, :auto_post, :status)
                RETURNING id
            """
            
            schedule_id = str(uuid.uuid4())
            values = {
                "id": schedule_id,
                "post_id": post_id,
                "scheduled_at": scheduled_at,
                "time_zone": time_zone,
                "priority": priority,
                "auto_post": auto_post,
                "status": "pending"
            }
            
            await db_manager.execute_query(query, values)
            return schedule_id
            
        except Exception as e:
            print(f"Error saving posting schedule: {e}")
            raise
    
    @staticmethod
    async def create_batch_operation(
        description: str,
        num_posts: int,
        days_duration: int,
        created_by: str = None
    ) -> str:
        """Create a new batch operation record"""
        try:
            query = """
                INSERT INTO batch_operations (id, description, num_posts, days_duration,
                                            status, created_by)
                VALUES (:id, :description, :num_posts, :days_duration,
                       :status, :created_by)
                RETURNING id
            """
            
            batch_id = str(uuid.uuid4())
            values = {
                "id": batch_id,
                "description": description,
                "num_posts": num_posts,
                "days_duration": days_duration,
                "status": "in_progress",
                "created_by": created_by
            }
            
            await db_manager.execute_query(query, values)
            return batch_id
            
        except Exception as e:
            print(f"Error creating batch operation: {e}")
            raise
    
    @staticmethod
    async def update_batch_operation_progress(
        batch_id: str,
        posts_generated: int = None,
        posts_failed: int = None,
        status: str = None,
        error_messages: List[str] = None
    ):
        """Update batch operation progress"""
        try:
            updates = []
            values = {"batch_id": batch_id}
            
            if posts_generated is not None:
                updates.append("posts_generated = :posts_generated")
                values["posts_generated"] = posts_generated
            
            if posts_failed is not None:
                updates.append("posts_failed = :posts_failed")
                values["posts_failed"] = posts_failed
            
            if status is not None:
                updates.append("status = :status")
                values["status"] = status
                
                if status in ["completed", "failed", "cancelled"]:
                    updates.append("completed_at = NOW()")
            
            if error_messages is not None:
                updates.append("error_messages = :error_messages")
                values["error_messages"] = error_messages
            
            if updates:
                query = f"""
                    UPDATE batch_operations 
                    SET {', '.join(updates)}
                    WHERE id = :batch_id
                """
                await db_manager.execute_query(query, values)
                
        except Exception as e:
            print(f"Error updating batch operation: {e}")
            raise
    
    @staticmethod
    async def get_post_by_id(post_id: str) -> Optional[Dict[str, Any]]:
        """Get a post by ID with all related data"""
        try:
            query = """
                SELECT p.*, c.name as campaign_name,
                       array_agg(DISTINCT jsonb_build_object(
                           'id', i.id,
                           'file_path', i.file_path,
                           'generation_method', i.generation_method
                       )) FILTER (WHERE i.id IS NOT NULL) as images,
                       array_agg(DISTINCT jsonb_build_object(
                           'id', cap.id,
                           'content', cap.content,
                           'generation_method', cap.generation_method
                       )) FILTER (WHERE cap.id IS NOT NULL) as captions,
                       array_agg(DISTINCT jsonb_build_object(
                           'id', ps.id,
                           'scheduled_at', ps.scheduled_at,
                           'status', ps.status,
                           'priority', ps.priority
                       )) FILTER (WHERE ps.id IS NOT NULL) as schedules
                FROM posts p
                LEFT JOIN campaigns c ON p.campaign_id = c.id
                LEFT JOIN images i ON p.id = i.post_id
                LEFT JOIN captions cap ON p.id = cap.post_id
                LEFT JOIN posting_schedules ps ON p.id = ps.post_id
                WHERE p.id = :post_id
                GROUP BY p.id, c.name
            """
            
            result = await db_manager.fetch_one(query, {"post_id": post_id})
            return dict(result) if result else None
            
        except Exception as e:
            print(f"Error getting post: {e}")
            return None
    
    @staticmethod
    async def get_recent_posts(limit: int = 10, user_id: str = None) -> List[Dict[str, Any]]:
        """Get recent posts with basic info, optionally filtered by user"""
        try:
            if user_id:
                query = """
                    SELECT p.id, p.original_description, p.caption, p.image_path,
                           p.status, p.platforms, p.scheduled_at, p.created_at, p.batch_id,
                           p.campaign_name, c.name as campaign_table_name,
                           p.engagement_metrics
                    FROM posts p
                    LEFT JOIN campaigns c ON p.campaign_id = c.id
                    WHERE p.user_id = :user_id
                    ORDER BY p.created_at DESC
                    LIMIT :limit
                """
                results = await db_manager.fetch_all(query, {"limit": limit, "user_id": user_id})
            else:
                query = """
                    SELECT p.id, p.original_description, p.caption, p.image_path,
                           p.status, p.platforms, p.scheduled_at, p.created_at, p.batch_id,
                           p.campaign_name, c.name as campaign_table_name,
                           p.engagement_metrics
                    FROM posts p
                    LEFT JOIN campaigns c ON p.campaign_id = c.id
                    ORDER BY p.created_at DESC
                    LIMIT :limit
                """
                results = await db_manager.fetch_all(query, {"limit": limit})
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting recent posts: {e}")
            return []
    
    @staticmethod
    async def get_scheduled_posts(user_id: str = None) -> List[Dict[str, Any]]:
        """Get posts scheduled for posting, optionally filtered by user"""
        try:
            if user_id:
                query = """
                    SELECT p.id, p.original_description, p.caption, p.image_path,
                           p.scheduled_at, p.platforms, p.subreddit, p.status,
                           COALESCE(p.campaign_name, c.name, 'Untitled Campaign') as campaign_name
                    FROM posts p
                    LEFT JOIN campaigns c ON p.campaign_id = c.id
                    WHERE p.status = 'scheduled' 
                      AND p.scheduled_at IS NOT NULL
                      AND p.scheduled_at <= NOW() + INTERVAL '7 days'
                      AND p.user_id = :user_id
                    ORDER BY p.scheduled_at ASC
                """
                results = await db_manager.fetch_all(query, {"user_id": user_id})
            else:
                query = """
                    SELECT p.id, p.original_description, p.caption, p.image_path,
                           p.scheduled_at, p.platforms, p.subreddit, p.status,
                           COALESCE(p.campaign_name, c.name, 'Untitled Campaign') as campaign_name
                    FROM posts p
                    LEFT JOIN campaigns c ON p.campaign_id = c.id
                    WHERE p.status = 'scheduled' 
                      AND p.scheduled_at IS NOT NULL
                      AND p.scheduled_at <= NOW() + INTERVAL '7 days'
                    ORDER BY p.scheduled_at ASC
                """
                results = await db_manager.fetch_all(query)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting scheduled posts: {e}")
            return []
    
    @staticmethod
    async def get_batch_operation_status(batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch operation status"""
        try:
            query = """
                SELECT * FROM batch_operations WHERE id = :batch_id
            """
            
            result = await db_manager.fetch_one(query, {"batch_id": batch_id})
            return dict(result) if result else None
            
        except Exception as e:
            print(f"Error getting batch operation: {e}")
            return None
    
    @staticmethod
    async def get_posts_by_batch_id(batch_id: str) -> List[Dict[str, Any]]:
        """Get all posts for a specific batch ID"""
        try:
            query = """
                SELECT p.id, p.user_id, p.original_description, p.caption, p.image_path,
                       p.status, p.platforms, p.scheduled_at, p.created_at, p.batch_id,
                       COALESCE(p.campaign_name, c.name, 'Untitled Campaign') as campaign_name
                FROM posts p
                LEFT JOIN campaigns c ON p.campaign_id = c.id
                WHERE p.batch_id = :batch_id
                ORDER BY p.created_at ASC
            """
            
            results = await db_manager.fetch_all(query, {"batch_id": batch_id})
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting posts by batch ID: {e}")
            return []
    
    @staticmethod
    async def schedule_batch_posts(
        batch_id: str,
        platforms: List[str],
        schedule_times: List[str],
        days: int,
        user_id: str = None  # 🔧 Accept user_id parameter
    ) -> bool:
        """Schedule all posts in a batch with specified platforms and times"""
        try:
            # Get all posts in the batch
            posts = await DatabaseService.get_posts_by_batch_id(batch_id)
            
            if not posts:
                raise Exception("No posts found in batch")
            
            # Update each post with platforms and scheduled time
            for i, post in enumerate(posts):
                if i < len(schedule_times):
                    scheduled_at = schedule_times[i]
                    
                    # Update post with platforms and scheduled time
                    update_query = """
                        UPDATE posts 
                        SET platforms = :platforms, scheduled_at = :scheduled_at, status = 'scheduled'
                        WHERE id = :post_id
                    """
                    
                    await db_manager.execute_query(update_query, {
                        "platforms": platforms,
                        "scheduled_at": scheduled_at,
                        "post_id": post['id']
                    })
                    
                    # Create posting schedule record
                    await DatabaseService.save_posting_schedule(
                        post_id=post['id'],
                        scheduled_at=scheduled_at,
                        platforms=platforms
                    )
                    
                    # 🔧 FIX: Create calendar event for scheduled post
                    try:
                        # Create meaningful title from campaign name or description
                        event_title = ''
                        if post.get('campaign_name') and post['campaign_name'].strip() and post['campaign_name'] != 'Untitled Campaign':
                            event_title = post['campaign_name'].strip()
                        elif post.get('original_description') and len(post['original_description'].strip()) > 10:
                            desc = post['original_description'].strip()
                            # Avoid UUID-like strings
                            if not (desc.startswith('Post ') and len(desc.split('-')) > 3):
                                event_title = f"{desc[:50]}..." if len(desc) > 50 else desc
                            else:
                                event_title = "Campaign Post"
                        elif post.get('caption') and post['caption'].strip():
                            caption = post['caption'].strip()
                            event_title = f"{caption[:40]}..." if len(caption) > 40 else caption
                        else:
                            event_title = "Social Media Campaign"
                        
                        # Create calendar event
                        await DatabaseService.create_calendar_event(
                            post_id=post['id'],
                            user_id=user_id or post.get('user_id', '00000000-0000-0000-0000-000000000000'),  # 🔧 Use passed user_id first
                            title=event_title,
                            description=post.get('caption', '') or post.get('original_description', ''),
                            start_time=datetime.fromisoformat(scheduled_at.replace('Z', '+00:00')) if isinstance(scheduled_at, str) else scheduled_at,
                            end_time=datetime.fromisoformat(scheduled_at.replace('Z', '+00:00')) if isinstance(scheduled_at, str) else scheduled_at,
                            status='scheduled',
                            platforms=platforms
                        )
                        
                        print(f"✅ Created calendar event for post {post['id']}: {event_title}")
                        
                    except Exception as calendar_error:
                        print(f"⚠️ Warning: Failed to create calendar event for post {post['id']}: {calendar_error}")
                        # Don't fail the entire scheduling operation if calendar event creation fails
            
            return True
            
        except Exception as e:
            print(f"Error scheduling batch posts: {e}")
            return False
    
    @staticmethod
    async def get_default_campaign_id() -> Optional[str]:
        """Get the default campaign ID"""
        try:
            query = """
                SELECT id FROM campaigns 
                WHERE name = 'Default Campaign' AND is_active = true
                LIMIT 1
            """
            
            result = await db_manager.fetch_one(query)
            return str(result['id']) if result else None
            
        except Exception as e:
            print(f"Error getting default campaign: {e}")
            return None
    
    @staticmethod
    async def get_database_stats() -> Dict[str, Any]:
        """Get database statistics"""
        try:
            queries = {
                "total_posts": "SELECT COUNT(*) as count FROM posts",
                "total_images": "SELECT COUNT(*) as count FROM images",
                "total_captions": "SELECT COUNT(*) as count FROM captions",
                "pending_schedules": "SELECT COUNT(*) as count FROM posting_schedules WHERE status = 'pending'",
                "active_batches": "SELECT COUNT(*) as count FROM batch_operations WHERE status = 'in_progress'"
            }
            
            stats = {}
            for key, query in queries.items():
                result = await db_manager.fetch_one(query)
                stats[key] = result['count'] if result else 0
            
            return stats
            
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {}


    @staticmethod
    async def get_posts_due_for_publishing() -> List[Dict[str, Any]]:
        """Get posts that are scheduled and due for publishing"""
        try:
            query = """
                SELECT id, platforms, caption, image_path, scheduled_at, original_description
                FROM posts 
                WHERE status = 'scheduled' 
                  AND scheduled_at <= NOW() 
                ORDER BY scheduled_at ASC
            """
            
            results = await db_manager.fetch_all(query)
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            print(f"Error getting posts due for publishing: {e}")
            return []
    
    @staticmethod
    async def count_scheduled_posts() -> int:
        """Count posts that are currently scheduled"""
        try:
            query = "SELECT COUNT(*) as count FROM posts WHERE status = 'scheduled'"
            result = await db_manager.fetch_one(query)
            return result['count'] if result else 0
            
        except Exception as e:
            print(f"Error counting scheduled posts: {e}")
            return 0
    
    @staticmethod
    async def get_recent_published_posts(limit: int = 5) -> List[Dict[str, Any]]:
        """Get recently published posts"""
        try:
            query = """
                SELECT id, platforms, caption, posted_at, engagement_metrics
                FROM posts 
                WHERE status = 'published' 
                ORDER BY posted_at DESC
                LIMIT :limit
            """
            
            results = await db_manager.fetch_all(query, {"limit": limit})
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            print(f"Error getting recent published posts: {e}")
            return []
    
    @staticmethod
    async def delete_post(post_id: str) -> bool:
        """Delete a post and all its associated data"""
        try:
            # Delete in order: schedules -> captions -> images -> post
            # This avoids foreign key constraint issues
            
            # Delete posting schedules
            await db_manager.execute_query(
                "DELETE FROM posting_schedules WHERE post_id = :post_id",
                {"post_id": post_id}
            )
            
            # Delete captions
            await db_manager.execute_query(
                "DELETE FROM captions WHERE post_id = :post_id",
                {"post_id": post_id}
            )
            
            # Get image paths before deleting (to clean up files)
            image_query = "SELECT file_path FROM images WHERE post_id = :post_id"
            image_results = await db_manager.fetch_all(image_query, {"post_id": post_id})
            
            # Delete images from database
            await db_manager.execute_query(
                "DELETE FROM images WHERE post_id = :post_id",
                {"post_id": post_id}
            )
            
            # Delete the post itself
            result = await db_manager.execute_query(
                "DELETE FROM posts WHERE id = :post_id",
                {"post_id": post_id}
            )
            
            # Clean up image files from disk
            if image_results:
                for row in image_results:
                    file_path = row['file_path']
                    if file_path and file_path.startswith('/public/'):
                        # Remove leading slash and try to delete file
                        local_path = file_path[1:]  # Remove leading slash
                        try:
                            if os.path.exists(local_path):
                                os.remove(local_path)
                                print(f"Deleted image file: {local_path}")
                        except Exception as file_error:
                            print(f"Warning: Could not delete image file {local_path}: {file_error}")
            
            print(f"Successfully deleted post {post_id} and associated data")
            return True
            
        except Exception as e:
            print(f"Error deleting post {post_id}: {e}")
            return False
    
    @staticmethod
    async def clear_all_posts() -> bool:
        """Clear all posts from the database (for testing purposes)"""
        try:
            # Delete in order: schedules -> captions -> images -> posts
            # This avoids foreign key constraint issues
            
            # Delete posting schedules
            await db_manager.execute_query("DELETE FROM posting_schedules")
            
            # Delete captions
            await db_manager.execute_query("DELETE FROM captions")
            
            # Delete images
            await db_manager.execute_query("DELETE FROM images")
            
            # Delete posts
            await db_manager.execute_query("DELETE FROM posts")
            
            print("All posts cleared from database")
            return True
            
        except Exception as e:
            print(f"Error clearing all posts: {e}")
            return False
    
    @staticmethod
    async def update_post_schedule(
        post_id: str,
        scheduled_at: datetime,
        status: str = "scheduled",
        platforms: List[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Update a post's schedule and create calendar event if needed"""
        try:
            # Update the post
            update_query = """
                UPDATE posts 
                SET scheduled_at = :scheduled_at, status = :status, platforms = :platforms
                WHERE id = :post_id
                RETURNING id, user_id, campaign_name, original_description, caption
            """
            
            result = await db_manager.fetch_one(update_query, {
                "post_id": post_id,
                "scheduled_at": scheduled_at,
                "status": status,
                "platforms": platforms
            })
            
            if not result:
                return False
            
            # Determine which user_id to use for the calendar event
            uid_to_use = str(result['user_id']) if result['user_id'] else (user_id if user_id else None)
            
            if uid_to_use:
                # Ensure the post has a user_id for consistency going forward
                if not result['user_id'] and user_id:
                    try:
                        await db_manager.execute_query(
                            "UPDATE posts SET user_id = :user_id WHERE id = :post_id",
                            {"user_id": user_id, "post_id": post_id}
                        )
                    except Exception:
                        # Don't block scheduling if this best-effort update fails
                        pass
                
                # Check if calendar event already exists
                existing_event_query = "SELECT id FROM calendar_events WHERE post_id = :post_id"
                existing_event = await db_manager.fetch_one(existing_event_query, {"post_id": post_id})
                
                if not existing_event:
                    # Create meaningful title from campaign name or description
                    event_title = ''
                    if result['campaign_name'] and result['campaign_name'].strip():
                        event_title = result['campaign_name'].strip()
                    elif result['original_description'] and len(result['original_description'].strip()) > 10:
                        desc = result['original_description'].strip()
                        event_title = f"{desc[:50]}..." if len(desc) > 50 else desc
                    elif result['caption'] and result['caption'].strip():
                        caption = result['caption'].strip()
                        event_title = f"{caption[:40]}..." if len(caption) > 40 else caption
                    else:
                        event_title = "Social Media Post"
                    
                    await DatabaseService.create_calendar_event(
                        post_id=post_id,
                        user_id=uid_to_use,
                        title=event_title,
                        description=result['caption'] or result['original_description'] or "",
                        start_time=scheduled_at,
                        end_time=scheduled_at,
                        status=status,
                        platforms=platforms or []
                    )
                    print(f"✅ Created calendar event for post {post_id}: {event_title}")
            
            return True
            
        except Exception as e:
            print(f"Error updating post schedule: {e}")
            return False
    
    @staticmethod
    async def create_calendar_event(
        post_id: str,
        user_id: str,
        title: str,
        description: str = "",
        start_time: datetime = None,
        end_time: datetime = None,
        status: str = "scheduled",
        platforms: List[str] = None
    ) -> str:
        """Create a calendar event for a scheduled post"""
        try:
            if not start_time:
                start_time = datetime.now()
            if not end_time:
                end_time = start_time
            
            event_id = str(uuid.uuid4())
            query = """
                INSERT INTO calendar_events (id, post_id, user_id, title, description, 
                                           start_time, end_time, status, event_metadata)
                VALUES (:id, :post_id, :user_id, :title, :description, 
                       :start_time, :end_time, :status, :event_metadata)
                RETURNING id
            """
            
            values = {
                "id": event_id,
                "post_id": post_id,
                "user_id": user_id,
                "title": title,
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "event_metadata": {"platforms": platforms or []}
            }
            
            await db_manager.execute_query(query, values)
            print(f"Created calendar event {event_id} for post {post_id}")
            return event_id
            
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            raise


# Global service instance
db_service = DatabaseService()
