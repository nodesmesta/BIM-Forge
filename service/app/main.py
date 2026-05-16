import asyncio
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Dict, Set, Optional, List
from datetime import datetime

from .core.config import settings
from .core.logging_config import setup_logging
from .models.task import Task, TaskStatus, GenerateRequest, AgentResult
from .models.project_specification import ProjectSpecification, StructuredGenerateRequest
from .agents.render_agent import RenderAgent
from .agents.coordinator_agent import CoordinatorAgent
from .agents.architect_agent import ArchitectAgent
from .agents.ifc_geometry_agent_v2 import IFCGeometryAgentV2
from .agents.chatbot_agent import ChatBotAgent, get_chatbot_agent
from .agents.registry import register_all_agents, get_workflow_agents
from .core.event_bus import get_event_bus, EventType, Event
from .core.agent_registry import get_registry


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def broadcast(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass


manager = ConnectionManager()

# In-memory task store (use Redis in production)
tasks: Dict[str, Task] = {}

# Event bus
event_bus = get_event_bus()

# Agent progress tracking per task
agent_progress: Dict[str, Dict[str, dict]] = {}


async def agent_event_handler(event: Event):
    """Handle agent events and broadcast to WebSocket clients."""
    task_id = event.payload.get("task_id")
    if not task_id or task_id not in tasks:
        return

    task = tasks[task_id]
    agent_name = event.source_agent or event.payload.get("agent_name", "Unknown")

    # Initialize agent progress tracking for this task
    if task_id not in agent_progress:
        agent_progress[task_id] = {}

    # Handle different event types
    if event.type == EventType.AGENT_STARTED:
        agent_progress[task_id][agent_name] = {
            "status": "running",
            "progress": event.payload.get("progress", 0),
            "started_at": datetime.now().isoformat(),
            "current_phase": event.payload.get("current_phase", "Starting..."),
            "message": event.payload.get("message", f"{agent_name} started")
        }
        await manager.broadcast(task_id, {
            "type": "agent_started",
            "agent_name": agent_name,
            "progress": event.payload.get("progress", 0),
            "phase": event.payload.get("current_phase", "Starting..."),
            "agent_progress": agent_progress[task_id]
        })

    elif event.type == EventType.AGENT_PROGRESS:
        if agent_name not in agent_progress[task_id]:
            agent_progress[task_id][agent_name] = {}
        agent_progress[task_id][agent_name].update({
            "status": "running",
            "progress": event.payload.get("progress", 0),
            "current_phase": event.payload.get("current_phase", agent_progress[task_id][agent_name].get("current_phase", "Working...")),
            "message": event.payload.get("message", "")
        })
        await manager.broadcast(task_id, {
            "type": "agent_progress",
            "agent_name": agent_name,
            "progress": event.payload.get("progress", 0),
            "phase": event.payload.get("current_phase", ""),
            "message": event.payload.get("message", ""),
            "agent_progress": agent_progress[task_id]
        })

    elif event.type == EventType.AGENT_COMPLETE:
        if agent_name not in agent_progress[task_id]:
            agent_progress[task_id][agent_name] = {}
        agent_progress[task_id][agent_name].update({
            "status": "complete",
            "progress": 100,
            "completed_at": datetime.now().isoformat(),
            "duration": event.payload.get("duration", 0),
            "message": event.payload.get("message", f"{agent_name} completed")
        })
        await manager.broadcast(task_id, {
            "type": "agent_complete",
            "agent_name": agent_name,
            "progress": 100,
            "duration": event.payload.get("duration", 0),
            "agent_progress": agent_progress[task_id]
        })

    elif event.type == EventType.AGENT_FAILED:
        if agent_name not in agent_progress[task_id]:
            agent_progress[task_id][agent_name] = {}
        agent_progress[task_id][agent_name].update({
            "status": "failed",
            "progress": agent_progress[task_id][agent_name].get("progress", 0),
            "error": event.payload.get("error", ""),
            "message": f"Error: {event.payload.get('error', 'Unknown error')}"
        })
        await manager.broadcast(task_id, {
            "type": "agent_failed",
            "agent_name": agent_name,
            "error": event.payload.get("error", ""),
            "agent_progress": agent_progress[task_id]
        })

# Global agent instances
architect_agent: Optional[ArchitectAgent] = None
ifc_geometry_agent: Optional[IFCGeometryAgentV2] = None
render_agent: Optional[RenderAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    import logging
    setup_logging()
    logger = logging.getLogger(__name__)
    global architect_agent, ifc_geometry_agent, render_agent

    # Startup
    logger.info(f"Starting up with output dir: {settings.output_dir}")
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)

    # Register all agents
    registry = register_all_agents()
    logger.info(f"Registered {len(registry._agents)} agents")

    # Get all agents from registry (single source of truth)
    architect_agent = registry.get_agent("ArchitectAgent")
    if architect_agent:
        logger.info("ArchitectAgent initialized from registry (with CoordinatorAgent dependency)")
    else:
        logger.error("ArchitectAgent not found in registry")
        architect_agent = None

    ifc_geometry_agent = registry.get_agent("IFCGeometryAgentV2")
    if ifc_geometry_agent:
        logger.info("IFCGeometryAgent initialized from registry")

    render_agent = registry.get_agent("RenderAgent")
    if render_agent:
        logger.info("RenderAgent initialized from registry")

    # Subscribe to agent events for WebSocket broadcasting
    event_bus.subscribe(EventType.AGENT_STARTED, agent_event_handler)
    event_bus.subscribe(EventType.AGENT_PROGRESS, agent_event_handler)
    event_bus.subscribe(EventType.AGENT_COMPLETE, agent_event_handler)
    event_bus.subscribe(EventType.AGENT_FAILED, agent_event_handler)
    logger.info("Subscribed to agent events for WebSocket broadcasting")

    yield

    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Building Generator API",
    description="AI-powered multi-agent building specification to 3D render generator with revision support",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint redirects to API docs
@app.get("/")
async def root():
    """Root endpoint redirects to API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


async def process_task_with_agents(task: Task):
    """
    Process a generation task with full workflow:
    1. ArchitectAgent - Generate architectural blueprint using LLM (Gemini)
    2. CoordinatorAgent - Merge designs into building layout with walls, doors, windows
    3. IFCGeometryAgent - Create IFC file with location and climate data
    4. RenderAgent - Render 3D image from IFC
    """
    import logging
    logger = logging.getLogger(__name__)
    context = {}
    registry = get_registry()

    try:
        # Step 1: Run ArchitectAgent (LLM-driven) to generate architectural blueprint
        architect_agent = registry.get_agent("ArchitectAgent")
        if architect_agent:
            logger.info(f"[TASK] Running ArchitectAgent (LLM-driven)... task_id={task.id}")
            task.status = TaskStatus.SPEC_GENERATING
            task.progress = 10
            await manager.broadcast(task.id, {"status": task.status.value, "progress": task.progress})

            # Publish agent start event
            await event_bus.publish(
                EventType.AGENT_STARTED,
                payload={"task_id": task.id, "agent_name": "ArchitectAgent", "progress": 10, "current_phase": "Parsing prompt & generating brief"},
                source_agent="ArchitectAgent"
            )

            context["specification"] = task.metadata["specification"]

            # Use execute_with_events for automatic event publishing
            context = await architect_agent.execute_with_events(task, context)
            logger.info(f"[TASK] ArchitectAgent completed successfully, progress={task.progress}")
            task.progress = 90

            # Publish agent complete event
            await event_bus.publish(
                EventType.AGENT_COMPLETE,
                payload={"task_id": task.id, "agent_name": "ArchitectAgent", "progress": 100, "duration": 0},
                source_agent="ArchitectAgent"
            )
            await manager.broadcast(task.id, {"status": task.status.value, "progress": task.progress})
        else:
            raise RuntimeError("ArchitectAgent not initialized")

        # Step 2: Run IFCGeometryAgent to create IFC file with location data
        ifc_geometry_agent = registry.get_agent("IFCGeometryAgentV2")
        if ifc_geometry_agent:
            logger.info(f"[TASK] Running IFCGeometryAgent... task_id={task.id}")
            task.status = TaskStatus.IFC_GENERATING

            # Publish agent start event
            await event_bus.publish(
                EventType.AGENT_STARTED,
                payload={"task_id": task.id, "agent_name": "IFCGeometryAgent", "progress": 90, "current_phase": "Creating IFC geometry"},
                source_agent="IFCGeometryAgent"
            )

            context = await ifc_geometry_agent.execute_with_events(task, context)
            logger.info(f"[TASK] IFCGeometryAgent completed successfully")
            task.progress = 95

            # Publish agent complete event
            await event_bus.publish(
                EventType.AGENT_COMPLETE,
                payload={"task_id": task.id, "agent_name": "IFCGeometryAgent", "progress": 100, "duration": 0},
                source_agent="IFCGeometryAgent"
            )
            await manager.broadcast(task.id, {"status": task.status.value, "progress": task.progress})
        else:
            raise RuntimeError("IFCGeometryAgent not initialized")

        # Step 3: Run RenderAgent to render 3D image
        render_agent = registry.get_agent("RenderAgent")
        if render_agent:
            logger.info(f"[TASK] Running RenderAgent... task_id={task.id}")
            task.status = TaskStatus.RENDERING

            # Publish agent start event
            await event_bus.publish(
                EventType.AGENT_STARTED,
                payload={"task_id": task.id, "agent_name": "RenderAgent", "progress": 95, "current_phase": "Rendering 3D image"},
                source_agent="RenderAgent"
            )

            context = await render_agent.execute_with_events(task, context)
            logger.info(f"[TASK] RenderAgent completed successfully")
            task.progress = 100

            # Publish agent complete event
            await event_bus.publish(
                EventType.AGENT_COMPLETE,
                payload={"task_id": task.id, "agent_name": "RenderAgent", "progress": 100, "duration": 0},
                source_agent="RenderAgent"
            )
            await manager.broadcast(task.id, {"status": task.status.value, "progress": task.progress})
        else:
            raise RuntimeError("RenderAgent not initialized")

        # Broadcast final status
        logger.info(f"[TASK] Task completed successfully: {task.id}")
        await manager.broadcast(task.id, {
            "status": task.status.value,
            "progress": task.progress,
            "context": context,
            "quality_score": task.quality_score,
            "revision_number": task.revision_number
        })

    except Exception as e:
        import traceback as tb
        import logging
        logger = logging.getLogger(__name__)
        
        task.status = TaskStatus.FAILED
        error_msg = str(e)
        full_trace = tb.format_exc()
        
        # Log error instead of print (avoids BrokenPipeError)
        logger.error(f"[TASK] UNCAUGHT ERROR in task {task.id}: {error_msg}")
        logger.error(full_trace)
        
        # Store error details
        task.error_message = error_msg
        task.result = {"error": error_msg, "traceback": full_trace}
        
        # Try to broadcast error status
        try:
            await manager.broadcast(task.id, {
                "status": task.status.value,
                "error": error_msg,
                "progress": task.progress
            })
        except Exception as broadcast_err:
            logger.warning(f"[TASK] Failed to broadcast error: {broadcast_err}")


@app.post("/api/webhook/github")
async def github_webhook(request: dict):
    """GitHub webhook: auto git pull on push events."""
    import subprocess, hmac, hashlib
    import logging
    logger = logging.getLogger(__name__)

    # Basic validation - check for push event
    # In production, verify X-Hub-Signature-256 with a webhook secret
    logger.info(f"Webhook received: ref={request.get('ref', 'unknown')}")

    try:
        repo_path = "/root/Arsitektur"
        result = subprocess.run(
            ["git", "-C", repo_path, "pull", "origin", "main"],
            capture_output=True, text=True, timeout=30,
            env={"GIT_SSH_COMMAND": "ssh -o StrictHostKeyChecking=accept-new"}
        )
        logger.info(f"Git pull result: {result.stdout.strip()}")
        if result.returncode != 0:
            logger.error(f"Git pull failed: {result.stderr}")
            return {"status": "error", "message": result.stderr}
        return {"status": "ok", "output": result.stdout.strip()}
    except Exception as e:
        logger.error(f"Webhook git pull exception: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/generate")
async def generate(request: StructuredGenerateRequest):
    """Generate building from structured specification only."""
    task_id = str(uuid.uuid4())

    # Only accept structured specifications
    if not request.is_structured or not request.specification:
        return {"error": "Only structured specification is supported. Please set is_structured=true and provide specification."}, 400

    # Store structured spec in prompt as JSON for agents to parse
    import json
    structured_prompt = json.dumps(request.specification.dict(), indent=2)
    task = Task(
        id=task_id,
        prompt=structured_prompt,
        max_revisions=request.max_revisions
    )
    # Add structured spec to task metadata for easy access
    task.metadata = {"is_structured": True, "specification": request.specification.dict()}

    tasks[task_id] = task

    # Start task processing in background
    asyncio.create_task(process_task_with_agents(task))

    # Broadcast initial status
    await manager.broadcast(task_id, {
        "status": task.status.value,
        "task_id": task_id,
        "progress": task.progress
    })

    return {"task_id": task_id, "status": "pending"}


@app.post("/api/chatbot")
async def chatbot_parse(request: dict):
    """
    Chat endpoint: Convert natural language prompt to structured specification.
    
    This endpoint supports conversation-based specification building:
    - First message: Parse initial prompt and identify missing info
    - Subsequent messages: Update specification based on user responses
    - Returns clarifying questions if specification is incomplete
    
    Request body:
        - prompt: User's message
        - session_data: Optional session state from previous responses
    
    Returns:
        - message: Response to show user
        - is_complete: Whether specification is ready
        - specification: Complete spec if is_complete=True
        - parsed_info: Summary of parsed data
        - session_data: Session state for next turn
        - needs_questions: Whether we need more info
    """
    prompt = request.get("prompt", "")
    session_data = request.get("session_data")
    
    if not prompt or not prompt.strip():
        return {
            "success": False,
            "message": "Please tell me about the building you'd like to create. What's your vision?",
            "specification": None,
            "parsed_info": None,
            "is_complete": False,
            "needs_questions": True
        }
    
    try:
        # Use ChatBotAgent to process the prompt
        chatbot = get_chatbot_agent()
        result = await chatbot.process(prompt, session_data)
        
        return {
            "success": True,
            "message": result.get("message", ""),
            "specification": result.get("specification"),
            "parsed_info": result.get("parsed_info"),
            "is_complete": result.get("is_complete", False),
            "needs_questions": result.get("needs_questions", False),
            "session_data": result.get("session_data")
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Something went wrong: {str(e)}",
            "specification": None,
            "parsed_info": None,
            "is_complete": False,
            "needs_questions": True
        }


@app.get("/api/tasks")
async def list_tasks(status_filter: Optional[str] = None):
    """List all tasks with optional status filter."""
    task_list = []
    for task_id, task in tasks.items():
        task_data = {
            "id": task.id,
            "status": task.status.value,
            "progress": task.progress,
            "prompt": task.prompt[:100] + "..." if len(task.prompt) > 100 else task.prompt,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "retry_count": task.retry_count,
            "revision_number": task.revision_number,
            "quality_score": task.quality_score,
        }

        if status_filter and task.status.value != status_filter:
            continue

        task_list.append(task_data)

    return {"tasks": task_list, "total": len(task_list)}


@app.get("/api/tasks/active")
async def list_active_tasks():
    """List all active (non-completed) tasks."""
    task_list = []
    for task_id, task in tasks.items():
        if task.status.value not in ["completed", "failed"]:
            task_data = {
                "id": task.id,
                "status": task.status.value,
                "progress": task.progress,
                "prompt": task.prompt[:100] + "..." if len(task.prompt) > 100 else task.prompt,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "retry_count": task.retry_count,
                "revision_number": task.revision_number,
                "quality_score": task.quality_score,
            }
            task_list.append(task_data)

    return {"tasks": task_list, "total": len(task_list)}


@app.get("/api/tasks/stats")
async def get_task_stats():
    """Get task statistics."""
    stats = {
        "total": len(tasks),
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "failed": 0,
        "by_status": {}
    }

    for task_id, task in tasks.items():
        status = task.status.value
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        if status == "pending":
            stats["pending"] += 1
        elif status in ["completed", "approved"]:
            stats["completed"] += 1
        elif status == "failed":
            stats["failed"] += 1
        else:
            stats["in_progress"] += 1

    return stats


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """Get task status."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    return {
        "id": task.id,
        "status": task.status.value,
        "progress": task.progress,
        "error_message": task.error_message,
        "result": task.result,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "retry_count": task.retry_count,
        "revision_number": task.revision_number,
        "quality_score": task.quality_score,
        "quality_status": task.quality_status.value if task.quality_status else None,
        "validation_issues": [issue.model_dump() for issue in task.validation_issues],
    }


@app.get("/api/gallery")
async def get_gallery():
    """Get list of all completed renders."""
    gallery = []
    output_path = Path(settings.output_dir)

    for png_file in output_path.glob("*.png"):
        if "_thumb" not in png_file.name:
            task_id = png_file.stem
            task = tasks.get(task_id)

            gallery.append({
                "id": task_id,
                "thumbnail": f"/api/gallery/{task_id}/thumb",
                "image": f"/api/gallery/{task_id}",
                "obj": f"/api/gallery/{task_id}/obj",
                "status": task.status.value if task else "unknown",
                "created_at": task.created_at.isoformat() if task and task.created_at else None,
            })

    return gallery


@app.get("/api/gallery/{task_id}")
async def get_render(task_id: str):
    """Get specific render image."""
    render_path = Path(settings.output_dir) / f"{task_id}.png"
    if not render_path.exists():
        raise HTTPException(status_code=404, detail="Render not found")

    return FileResponse(str(render_path))


@app.get("/api/gallery/{task_id}/thumb")
async def get_thumbnail(task_id: str):
    """Get thumbnail image."""
    thumb_path = Path(settings.output_dir) / f"{task_id}_thumb.png"
    render_path = Path(settings.output_dir) / f"{task_id}.png"

    if thumb_path.exists():
        return FileResponse(str(thumb_path))
    elif render_path.exists():
        return FileResponse(str(render_path))
    else:
        raise HTTPException(status_code=404, detail="Image not found")


@app.get("/api/gallery/{task_id}/obj")
async def get_obj(task_id: str):
    """Get OBJ file."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    obj_path = Path(settings.output_dir) / f"{task_id}.obj"
    if not obj_path.exists():
        raise HTTPException(status_code=404, detail="OBJ file not found")

    return FileResponse(str(obj_path), media_type="text/plain", filename=f"{task_id}.obj")


@app.get("/api/gallery/{task_id}/revision")
async def get_revision_history(task_id: str):
    """Get revision history for a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    return {
        "total_revisions": task.revision_number,
        "history": [
            {
                "revision_number": r.revision_number,
                "status": r.status.value,
                "reason": r.reason,
                "affected_agents": r.affected_agents,
                "phase": r.phase
            }
            for r in task.revision_history
        ]
    }


@app.get("/api/gallery/{task_id}/quality")
async def get_quality_report(task_id: str):
    """Get quality report for a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    report = {
        "quality_score": task.quality_score,
        "quality_status": task.quality_status.value if task.quality_status else None,
        "validation_issues": [i.model_dump() for i in task.validation_issues]
    }

    return report


@app.websocket("/api/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task updates."""
    await manager.connect(websocket, task_id)

    # Send initial connection confirmation
    await websocket.send_json({
        "type": "connected",
        "task_id": task_id,
        "message": "WebSocket connected successfully"
    })

    try:
        # Keep connection alive and listen for incoming messages
        while True:
            # Wait for any message (ping) from client to keep connection alive
            data = await websocket.receive_text()
            # Optional: handle ping/pong or client messages
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"WebSocket disconnected for task {task_id}")


@app.get("/api/agents")
async def list_agents():
    """List all registered agents and their status."""
    registry = get_registry()
    return registry.get_health_report()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    registry = get_registry()
    agent_statuses = registry.get_agent_statuses()

    return {
        "status": "healthy",
        "gemini_api_enabled": True,  # Always enabled if PROJECT_ID, LOCATION, MODEL env vars are set
        "agents": {name: status.value for name, status in agent_statuses.items()}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
