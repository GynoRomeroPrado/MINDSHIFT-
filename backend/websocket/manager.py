"""
WebSocket Manager for Real-time Features
Supports real-time notifications, chat updates, and live dashboard updates
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        # user_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # organization_id -> Set[user_ids]
        self.organization_connections: Dict[int, Set[int]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, organization_id: int):
        """Accept and register new WebSocket connection"""
        await websocket.accept()

        # Add to active connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

        # Add to organization connections
        if organization_id not in self.organization_connections:
            self.organization_connections[organization_id] = set()
        self.organization_connections[organization_id].add(user_id)

        logger.info(f"WebSocket connected: user_id={user_id}, org_id={organization_id}")

    def disconnect(self, websocket: WebSocket, user_id: int, organization_id: int):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        if organization_id in self.organization_connections:
            self.organization_connections[organization_id].discard(user_id)
            if not self.organization_connections[organization_id]:
                del self.organization_connections[organization_id]

        logger.info(f"WebSocket disconnected: user_id={user_id}")

    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to specific user (all their connections)"""
        if user_id in self.active_connections:
            dead_connections = []

            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")
                    dead_connections.append(connection)

            # Remove dead connections
            for conn in dead_connections:
                self.active_connections[user_id].remove(conn)

    async def broadcast_to_organization(self, message: dict, organization_id: int, exclude_user_id: int = None):
        """Broadcast message to all users in organization"""
        if organization_id not in self.organization_connections:
            return

        for user_id in self.organization_connections[organization_id]:
            if exclude_user_id and user_id == exclude_user_id:
                continue

            await self.send_personal_message(message, user_id)

    async def send_burnout_alert(self, user_id: int, score: float, risk_level: str):
        """Send burnout alert to user"""
        message = {
            "type": "burnout_alert",
            "data": {
                "score": score,
                "risk_level": risk_level,
                "message": "New burnout assessment available"
            }
        }
        await self.send_personal_message(message, user_id)

    async def send_intervention_notification(self, user_id: int, intervention: dict):
        """Send intervention notification"""
        message = {
            "type": "intervention",
            "data": intervention
        }
        await self.send_personal_message(message, user_id)

    async def send_dashboard_update(self, organization_id: int, stats: dict):
        """Send dashboard update to organization"""
        message = {
            "type": "dashboard_update",
            "data": stats
        }
        await self.broadcast_to_organization(message, organization_id)


# Global connection manager
manager = ConnectionManager()
