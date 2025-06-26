"""Notification router with real-time WebSocket support."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Query
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.api.v1.dependencies import get_db
from app.core.auth import auth_manager
from app.core.config import settings
from app.models.user_model import User
from app.domain.repositories.user_repository import UserRepository
from app.schemas.notification_schema import (
    NotificationCreate,
    NotificationResponse,
    NotificationUpdate,
)
from app.services.notification_service import NotificationService, connection_manager

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def get_websocket_user(token: str, db: Session) -> User:
    """Authenticate WebSocket connection using token."""
    if not token:
        raise ValueError("No token provided")
    
    try:
        payload: dict = jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise ValueError("Invalid token payload")
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")

    repo = UserRepository(db)
    user: User | None = repo.get_by_id(user_id)
    if user is None:
        raise ValueError("User not found")
    return user


@router.websocket("/ws/{user_id}")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: UUID,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time notifications."""
    try:
        # Authenticate WebSocket connection using token from query parameter
        if token:
            try:
                current_user = await get_websocket_user(token, db)
                
                # Verify the user_id matches the token
                if str(current_user.user_id) != str(user_id):
                    await websocket.close(code=1008, reason="Unauthorized: User ID mismatch")
                    return
                    
                user_role = current_user.roles[0].role_name if current_user.roles else "user"
            except Exception as auth_error:
                print(f"WebSocket authentication failed: {auth_error}")
                await websocket.close(code=1008, reason="Authentication failed")
                return
        else:
            # Close connection if no token provided
            print(f"WebSocket connection without token for user {user_id}")
            await websocket.close(code=1008, reason="Token required")
            return
        
        # Initialize notification service
        notification_service = NotificationService(db)
        
        # Handle the WebSocket connection
        await notification_service.handle_websocket_connection(
            websocket, user_id, user_role
        )
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Get notifications for the current user."""
    notification_service = NotificationService(db)
    return notification_service.get_user_notifications(
        user_id=current_user.user_id,
        skip=skip,
        limit=limit,
        unread_only=unread_only
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications."""
    notification_service = NotificationService(db)
    count = notification_service.get_unread_count(current_user.user_id)
    return {"count": count}


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new notification (admin only)."""
    # Check if user has permission to create notifications
    if not any(role.role_name in ["admin", "super_admin"] for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create notifications"
        )
    
    notification_service = NotificationService(db)
    return await notification_service.create_notification(notification_data)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    notification_service = NotificationService(db)
    notification = notification_service.mark_as_read(notification_id, current_user.user_id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return notification


@router.patch("/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the current user."""
    notification_service = NotificationService(db)
    count = notification_service.mark_all_as_read(current_user.user_id)
    return {"message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a notification."""
    notification_service = NotificationService(db)
    success = notification_service.delete_notification(notification_id, current_user.user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification deleted successfully"}


# Admin endpoints
@router.get("/admin/connected-users")
async def get_connected_users(
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of currently connected users (admin only)."""
    if not any(role.role_name in ["admin", "super_admin"] for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view connected users"
        )
    
    return {"connected_users": connection_manager.get_connected_users()}


@router.post("/admin/broadcast")
async def broadcast_notification(
    title: str,
    message: str,
    notification_type: str = "system_announcement",
    priority: str = "medium",
    target_role: Optional[str] = None,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Broadcast a notification to all users or specific role (admin only)."""
    if not any(role.role_name in ["admin", "super_admin"] for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can broadcast notifications"
        )
    
    notification_service = NotificationService(db)
    
    # Create notification without user_id for broadcast
    notification_data = NotificationCreate(
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority
    )
    
    # Create and send notification
    await notification_service.create_notification(notification_data, send_realtime=True)
    
    return {"message": "Notification broadcasted successfully"}


# Utility endpoints for triggering specific notification types
@router.post("/test/assessment-created")
async def test_assessment_created_notification(
    assessment_id: UUID,
    location_name: str,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Test endpoint for assessment created notification."""
    notification_service = NotificationService(db)
    await notification_service.notify_assessment_created(
        assessment_id, location_name, current_user.user_id
    )
    return {"message": "Assessment created notification sent"}


@router.post("/test/assessment-verified")
async def test_assessment_verified_notification(
    assessment_id: UUID,
    location_name: str,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Test endpoint for assessment verified notification."""
    notification_service = NotificationService(db)
    await notification_service.notify_assessment_verified(
        assessment_id, location_name, current_user.user_id
    )
    return {"message": "Assessment verified notification sent"}


@router.post("/test/location-added")
async def test_location_added_notification(
    location_name: str,
    region_name: str,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Test endpoint for location added notification."""
    if not any(role.role_name in ["admin", "super_admin"] for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can send location added notifications"
        )
    
    notification_service = NotificationService(db)
    await notification_service.notify_new_location_added(location_name, region_name)
    return {"message": "Location added notification sent"}


@router.post("/test/score-updated")
async def test_score_updated_notification(
    location_name: str,
    new_score: float,
    current_user: User = Depends(auth_manager.get_current_user),
    db: Session = Depends(get_db)
):
    """Test endpoint for score updated notification."""
    notification_service = NotificationService(db)
    await notification_service.notify_score_updated(
        location_name, new_score, current_user.user_id
    )
    return {"message": "Score updated notification sent"}

# Export the router with the expected name
notification_router = router
