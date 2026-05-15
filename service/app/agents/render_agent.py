import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from ..models.task import Task, TaskStatus
from ..core.config import settings
from .base import BaseAgent


class RenderAgent(BaseAgent):
    def __init__(self, output_dir: str, blender_path: str = None):
        super().__init__("RenderAgent")
        self.output_dir = Path(output_dir)
        self.blender_path = blender_path or settings.blender_path

    async def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        task.status = TaskStatus.RENDERING
        task.progress = 70

        try:
            if "ifc_path" not in context:
                raise KeyError("ifc_path not found in context")

            ifc_path = context["ifc_path"]
            task_id = task.id

            render_path = self.output_dir / f"{task_id}.png"
            thumbnail_path = self.output_dir / f"{task_id}_thumb.png"

            if not Path(ifc_path).exists():
                raise FileNotFoundError(f"IFC file not found: {ifc_path}")

            # Check if Blender is available
            import logging
            logger = logging.getLogger(__name__)
            if not self._is_blender_available():
                logger.warning("[RenderAgent] Blender not found, skipping render")
                context["render_skipped"] = True
                context["render_reason"] = "Blender not installed"
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                task.result = {
                    "ifc_path": f"/api/gallery/{task_id}/ifc",
                    "render_skipped": True,
                }
                return context

            quality = context.get("quality", "high")

            await self._run_render(ifc_path, str(render_path), str(thumbnail_path), quality)

            context["render_path"] = str(render_path)
            context["thumbnail_path"] = str(thumbnail_path)

            task.status = TaskStatus.COMPLETED
            task.progress = 100

            task.result = {
                "ifc_path": f"/api/gallery/{task_id}/ifc",
                "render_path": f"/api/gallery/{task_id}",
                "thumbnail_path": f"/api/gallery/{task_id}/thumb",
            }

            return context

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = f"Render failed: {str(e)}"
            raise

    def _is_blender_available(self) -> bool:
        """Check if Blender is installed and can execute."""
        import shutil
        import subprocess
        import os
        
        # Find blender binary
        blender_cmd = shutil.which("blender")
        if not blender_cmd and self.blender_path:
            blender_cmd = shutil.which(self.blender_path)
        
        if not blender_cmd:
            return False
        
        # Verify it can actually execute
        try:
            result = subprocess.run(
                [blender_cmd, "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    async def _run_render(self, ifc_path: str, output_path: str, thumbnail_path: str, quality: str = "high"):
        blender_script = Path(__file__).parent.parent.parent / "scripts" / "blender_render_fixed.py"

        cmd = [
            self.blender_path,
            "-b",
            "-P", str(blender_script),
            "--",
            "--ifc", ifc_path,
            "--output", output_path,
            "--thumbnail", thumbnail_path,
            "--quality", quality,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Blender render failed: {error_msg}")
