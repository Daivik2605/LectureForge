"""
WebSocket endpoint for real-time job progress updates.
"""

import asyncio
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
    status = None
    for attempt in range(5):
        try:
            status = await job_manager.get_job_status(job_id)
            break
        except JobNotFoundError:
            logger.info(f"WebSocket waiting for Job {job_id} to initialize (Attempt {attempt+1}/5).")
            await asyncio.sleep(1)

    if status is None:
        await websocket.send_json({
            "type": "error",
            "job_id": job_id,
            "data": {"error": "Job not found"},
            "timestamp": datetime.utcnow().isoformat(),
        })
        await websocket.close()
        return

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
    
    queue: asyncio.Queue[dict] = asyncio.Queue()
    stop_event = asyncio.Event()

    # Register callback for progress updates
    async def progress_callback(message: dict):
        await queue.put(message)

    job_manager.subscribe(job_id, progress_callback)

    async def subscriber_loop() -> None:
        while not stop_event.is_set():
            message = await queue.get()
            await manager.send_message(job_id, message)

    subscriber_task = asyncio.create_task(subscriber_loop())

    async def heartbeat_loop() -> None:
        while not stop_event.is_set():
            await asyncio.sleep(15)
            try:
                await websocket.send_json({"type": "hb"})
            except WebSocketDisconnect:
                stop_event.set()
                break
            except Exception:
                stop_event.set()
                break

    heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    try:
        # Keep connection alive and handle client messages
        while True:
            receive_task = asyncio.create_task(websocket.receive_text())
            done, pending = await asyncio.wait(
                {receive_task},
                timeout=15,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if receive_task in done:
                try:
                    data = receive_task.result()
                except WebSocketDisconnect:
                    raise
            
                # Handle ping/pong for keepalive
                if data == "ping":
                    await websocket.send_text("pong")
                
                # Handle cancel request
                elif data == "cancel":
                    await job_manager.cancel_job(job_id)
                    await websocket.send_json({
                        "type": "cancelled",
                        "job_id": job_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            for task in pending:
                task.cancel()
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
    finally:
        stop_event.set()
        subscriber_task.cancel()
        heartbeat_task.cancel()
        job_manager.unsubscribe(job_id, progress_callback)
        manager.disconnect(websocket, job_id)
