# Building Generator Backend

Backend API untuk aplikasi AI Agent yang menghasilkan gambar bangunan secara otomatis.

## Setup

### 1. Install Dependencies

```bash
cd service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup Environment Variables

```bash
cp .env.example .env
# Edit .env dan masukkan NVIDIA API key
```

### 3. Install IfcOpenShell

```bash
pip install ifcopenshell
```

### 4. Verify Blender Installation

```bash
blender --version
```

## Running the Server

### Development

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Setelah server running, akses dokumentasi API di:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/generate | Submit new generation task |
| GET | /api/status/{task_id} | Get task status |
| GET | /api/gallery | List all renders |
| GET | /api/gallery/{id} | Get render image |
| GET | /api/gallery/{id}/ifc | Get IFC file |
| WS | /api/ws/{task_id} | WebSocket for real-time updates |

## Architecture

```
service/
├── app/
│   ├── main.py              # FastAPI application
│   ├── agents/              # AI Agents
│   │   ├── spec_agent.py    # NVIDIA NIM specification generator
│   │   ├── ifc_agent.py     # IfcOpenShell IFC creator
│   │   └── render_agent.py  # Blender renderer
│   ├── core/
│   │   ├── config.py        # Configuration
│   │   └── nvidia_client.py # NVIDIA NIM API client
│   ├── models/
│   │   ├── specification.py # Building specification models
│   │   └── task.py          # Task status models
│   └── api/
│       └── routes/          # API routes
├── scripts/
│   └── blender_render.py    # Blender Python script
├── outputs/                 # Generated files
└── requirements.txt         # Python dependencies
```

## Workflow

1. User submits prompt via `/api/generate`
2. **Spec Agent** calls NVIDIA NIM API to parse prompt into building specification
3. **IFC Agent** creates IFC file using IfcOpenShell
4. **Render Agent** renders image using Blender
5. Results stored in `outputs/` directory
6. Frontend receives real-time updates via WebSocket
