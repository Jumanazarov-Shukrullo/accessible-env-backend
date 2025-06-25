"""Notification service for managing user notifications and real-time updates."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.domain.repositories.notification_repository import NotificationRepository
from app.models.notification_model import Notification
from app.schemas.notification_schema import (
    NotificationCreate,
    NotificationResponse,
    NotificationUpdate,
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID, user_role: str = None):
        """Connect a new WebSocket for a user."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            'user_id': user_id,
            'user_role': user_role,
            'connected_at': datetime.utcnow()
        }
        
        logger.info(f"WebSocket connected for user {user_id}, role: {user_role}")

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket."""
        if websocket in self.connection_metadata:
            user_id = self.connection_metadata[websocket]['user_id']
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, user_id: UUID):
        """Send a message to all connections of a specific user."""
        if user_id in self.active_connections:
            disconnected_connections = []
            
            for connection in self.active_connections[user_id].copy():
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected_connections.append(connection)
            
            # Clean up disconnected connections
            for connection in disconnected_connections:
                self.disconnect(connection)

    async def broadcast_to_role(self, message: dict, role: str):
        """Broadcast a message to all users with a specific role."""
        for websocket, metadata in self.connection_metadata.items():
            if metadata.get('user_role') == role:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to role {role}: {e}")

    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected users."""
        disconnected_connections = []
        
        for websocket in self.connection_metadata.keys():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected_connections.append(websocket)
        
        # Clean up disconnected connections
        for connection in disconnected_connections:
            self.disconnect(connection)

    def get_connected_users(self) -> List[Dict]:
        """Get list of currently connected users."""
        connected_users = []
        for websocket, metadata in self.connection_metadata.items():
            connected_users.append({
                'user_id': str(metadata['user_id']),
                'user_role': metadata.get('user_role'),
                'connected_at': metadata['connected_at'].isoformat()
            })
        return connected_users


# Global connection manager instance
connection_manager = ConnectionManager()


class NotificationService:
    """Service for managing notifications and real-time updates."""

    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = NotificationRepository(db)

    async def create_notification(
        self, 
        notification_data: NotificationCreate,
        send_realtime: bool = True
    ) -> NotificationResponse:
        """Create a new notification and optionally send real-time update."""
        try:
            # Create notification in database
            notification = self.notification_repo.create(notification_data)
            
            # Convert model to response schema with proper field mapping
            response = NotificationResponse(
                notification_id=notification.id,
                user_id=notification.user_id,
                title=notification.subject,
                message=notification.body,
                notification_type=notification.type.value,
                priority=self._int_to_priority(notification.priority),
                is_read=notification.is_read,
                created_at=notification.created_at,
                read_at=notification.read_at
            )
            
            # Send real-time notification if enabled
            if send_realtime:
                await self._send_realtime_notification(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise

    def _int_to_priority(self, priority_int: int) -> str:
        """Convert priority integer to string."""
        priority_map = {1: "low", 2: "medium", 3: "high"}
        return priority_map.get(priority_int, "medium")

    async def _send_realtime_notification(self, notification: NotificationResponse):
        """Send real-time notification via WebSocket."""
        message = {
            'type': 'notification',
            'data': {
                'notification_id': str(notification.notification_id),
                'title': notification.title,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'priority': notification.priority,
                'created_at': notification.created_at.isoformat(),
                'is_read': notification.is_read
            }
        }
        
        # Send to specific user if user_id is provided
        if notification.user_id:
            try:
                user_uuid = UUID(notification.user_id)
                await connection_manager.send_personal_message(message, user_uuid)
            except ValueError:
                print(f"Invalid user_id format: {notification.user_id}")
        else:
            # Broadcast to all users
            await connection_manager.broadcast_to_all(message)

    async def notify_assessment_created(self, assessment_id: UUID, location_name: str, user_id: UUID):
        """Send notification when a new assessment is created."""
        notification_data = NotificationCreate(
            user_id=user_id,
            title="Assessment Submitted",
            message=f"Your accessibility assessment for '{location_name}' has been submitted for review.",
            notification_type="assessment_created",
            priority="medium"
        )
        
        await self.create_notification(notification_data)

    async def notify_assessment_verified(self, assessment_id: UUID, location_name: str, user_id: UUID):
        """Send notification when an assessment is verified."""
        notification_data = NotificationCreate(
            user_id=user_id,
            title="Assessment Verified ✅",
            message=f"Your accessibility assessment for '{location_name}' has been verified and published!",
            notification_type="assessment_verified",
            priority="high"
        )
        
        await self.create_notification(notification_data)

    async def notify_new_location_added(self, location_name: str, region_name: str):
        """Broadcast notification when a new location is added."""
        notification_data = NotificationCreate(
            title="New Location Added 📍",
            message=f"A new location '{location_name}' in {region_name} is now available for assessment.",
            notification_type="location_added",
            priority="medium"
        )
        
        await self.create_notification(notification_data)

    async def notify_score_updated(self, location_name: str, new_score: float, user_id: UUID):
        """Send notification when location accessibility score is updated."""
        notification_data = NotificationCreate(
            user_id=user_id,
            title="Score Updated 📊",
            message=f"The accessibility score for '{location_name}' has been updated to {new_score:.1f}.",
            notification_type="score_updated",
            priority="low"
        )
        
        await self.create_notification(notification_data)

    async def notify_system_maintenance(self, message: str, start_time: datetime):
        """Broadcast system maintenance notification."""
        notification_data = NotificationCreate(
            title="System Maintenance 🔧",
            message=f"Scheduled maintenance: {message}. Starting at {start_time.strftime('%Y-%m-%d %H:%M')} UTC.",
            notification_type="system_maintenance",
            priority="high"
        )
        
        await self.create_notification(notification_data)

    def get_user_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False
    ) -> List[NotificationResponse]:
        """Get notifications for a specific user."""
        notifications = self.notification_repo.get_user_notifications(
            user_id=user_id,
            skip=skip,
            limit=limit,
            unread_only=unread_only
        )
        
        return [
            NotificationResponse(
                notification_id=n.id,
                user_id=n.user_id,
                title=n.subject,
                message=n.body,
                notification_type=n.type.value,
                priority=self._int_to_priority(n.priority),
                is_read=n.is_read,
                created_at=n.created_at,
                read_at=n.read_at
            ) for n in notifications
        ]

    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Optional[NotificationResponse]:
        """Mark a notification as read."""
        notification = self.notification_repo.mark_as_read(notification_id, user_id)
        if notification:
            return NotificationResponse(
                notification_id=notification.id,
                user_id=notification.user_id,
                title=notification.subject,
                message=notification.body,
                notification_type=notification.type.value,
                priority=self._int_to_priority(notification.priority),
                is_read=notification.is_read,
                created_at=notification.created_at,
                read_at=notification.read_at
            )
        return None

    def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        return self.notification_repo.mark_all_as_read(user_id)

    def delete_notification(self, notification_id: UUID, user_id: UUID) -> bool:
        """Delete a notification."""
        return self.notification_repo.delete(notification_id, user_id)

    def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user."""
        return self.notification_repo.get_unread_count(user_id)

    # Real-time WebSocket handlers
    async def handle_websocket_connection(self, websocket: WebSocket, user_id: UUID, user_role: str = None):
        """Handle WebSocket connection for real-time notifications."""
        await connection_manager.connect(websocket, user_id, user_role)
        
        try:
            # Send initial unread count
            unread_count = self.get_unread_count(user_id)
            await websocket.send_text(json.dumps({
                'type': 'unread_count',
                'data': {'count': unread_count}
            }))
            
            # Keep connection alive and handle incoming messages
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get('type') == 'mark_read':
                    notification_id = UUID(message.get('notification_id'))
                    self.mark_as_read(notification_id, user_id)
                    
                    # Send updated unread count
                    unread_count = self.get_unread_count(user_id)
                    await websocket.send_text(json.dumps({
                        'type': 'unread_count',
                        'data': {'count': unread_count}
                    }))
                
                elif message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({'type': 'pong'}))
                    
        except WebSocketDisconnect:
            connection_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
            connection_manager.disconnect(websocket)
