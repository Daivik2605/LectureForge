"""
WebSocket endpoint for real-time job progress updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime

from app.core.logging import get_logger
from app.services.job_manager import job_manager
from app.core.exceptions import JobNotFoundError

logger = get_logger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for job progress updates."""
    
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        
        logger.info(f"WebSocket connected for job {job_id}")
    
    def disconnect(self, websocket: WebSocket, job_id: str) -> None:
        """Remove a WebSocket connection."""
        if job_id in self.active_connections:
            self.active_connections[job_id] = [
                ws for ws in self.active_connections[job_id]
                if ws != websocket
            ]
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        
        logger.info(f"WebSocket disconnected for job {job_id}")
    
    async def send_message(self, job_id: str, message: dict) -> None:
        """Send message to all connections for a job."""
        if job_id in self.active_connections:
            dead_connections = []
            
            for websocket in self.active_connections[job_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    dead_connections.append(websocket)
            
            # Clean up dead connections
            for ws in dead_connections:
                self.disconnect(ws, job_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.
    
    Clients connect to receive:
    - Progress updates
    - Slide completion events
    - Completion/error notifications
    """
    await manager.connect(websocket, job_id)
    
    # Send initial status
    try:
        status = job_manager.get_job_status(job_id)
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "data": {
                "status": status.status.value,
                "progress": status.progress,
                "current_slide": status.current_slide,
                "total_slides": status.total_slides,
                "current_step": status.current_step,
            },
            "timestamp": datetime.utcnow().isoformat(),
        })
    except JobNotFoundError:
        await websocket.send_json({
            "type": "error",
            "job_id": job_id,
            "data": {"error": "Job not found"},
            "timestamp": datetime.utcnow().isoformat(),
        })
        await websocket.close()
        return
    
    # Register callback for progress updates
    async def progress_callback(message: dict):
        await manager.send_message(job_id, message)
    
    job_manager.subscribe(job_id, progress_callback)
    
    try:
        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()
            
            # Handle ping/pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")
            
            # Handle cancel request
            elif data == "cancel":
                job_manager.cancel_job(job_id)
                await websocket.send_json({
                    "type": "cancelled",
                    "job_id": job_id,
                    "timestamp": datetime.utcnow().isoformat(),
                })
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
    finally:
        job_manager.unsubscribe(job_id, progress_callback)
        manager.disconnect(websocket, job_id)
