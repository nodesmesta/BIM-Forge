# Backend generate utility: write IFC to disk with correct path
import os
import sys
import traceback
from pathlib import Path
from typing import Optional

import ifcopenshell


def get_outputs_dir(task_id: str) -> Path:
    """Ensure outputs directory exists and return absolute path for task file."""
    base_dir = Path(__file__).resolve().parents[2] / "service" / "outputs"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{task_id}.ifc"


def generate_ifc_for_task(task_id: str, agents_result: Optional[dict] = None) -> Optional[str]:
    """
    Export IFC memory model from agents to disk at outputs/<task_id>.ifc.
    Returns absolute path if successful, else None (and logs error).
    """
    try:
        target = get_outputs_dir(task_id)
        ifcopenshell.ifc4x3.schema(output_path=str(target), mode="w")
        # TODO: fill model here using agents_result
        # file = agents_result["model"] if agents_result else create_mem_model()
        # ifcopenshell.ifc4x3.schema(content=file, output_path=str(target), mode="w")
        if target.exists() and target.stat().st_size > 0:
            return str(target.resolve())
        raise IOError(f"File not found or zero size: {target}")
    except Exception:
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_ifc.py <task_id>", file=sys.stderr)
        sys.exit(1)
    task_id = sys.argv[1]
    path = generate_ifc_for_task(task_id)
    print(path)
