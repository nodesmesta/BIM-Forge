from pydantic_settings import BaseSettings
from enum import Enum
from pathlib import Path


class IFCSchema(str, Enum):
    IFC2X3 = "IFC2X3"
    IFC4 = "IFC4"
    IFC4X3 = "IFC4X3"




class Settings(BaseSettings):
    model_config = {
        "env_file": Path(__file__).parent.parent.parent / ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Validate output_dir is not relative path
        if self.output_dir.startswith("./") or self.output_dir.startswith("../"):
            raise ValueError(f"output_dir must be absolute path, got: {self.output_dir}")
    # Gemini/Vertex AI Configuration - REQUIRED
    project_id: str
    location: str
    model: str

    # Existing configurations - REQUIRED where applicable
    ifc_schema: IFCSchema
    redis_url: str
    output_dir: str
    blender_path: str
    blenderkit_api_key: str
    blenderkit_enabled: bool
    blenderkit_material_category: str
    blenderkit_furniture_style: str
    host: str
    port: int
    openweather_api_key: str
    retry_max_attempts: int
    retry_initial_delay: float
    retry_max_delay: float
    quality_min_score: float
    quality_max_revisions: int
    agent_max_concurrent: int
    agent_timeout: float

    # Layout and staircase parameters - REQUIRED
    margin_default: float
    grid_resolution: float
    riser_height: float
    tread_depth: float
    handrail_height: float

    # IFC Generation Parameters
    ifc_precision: float
    default_slab_thickness: float
    default_wall_thickness: float

    

settings = Settings()
__all__ = ["settings", "IFCSchema"]
