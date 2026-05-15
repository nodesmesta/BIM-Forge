#!/usr/bin/env python3
"""
Backend Test Runner
Menguji backend secara otomatis dan menangkap semua error dengan detail lengkap.
"""

import asyncio
import json
import sys
import time
import traceback
from pathlib import Path

# Add service to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx


class BackendTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)
        
    async def wait_for_backend(self, timeout: int = 30) -> bool:
        """Wait for backend to be ready."""
        print(f"[*] Menunggu backend di {self.base_url}...")
        for i in range(timeout):
            try:
                resp = await self.client.get(f"{self.base_url}/health")
                if resp.status_code == 200:
                    print(f"[+] Backend ready!")
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
        print(f"[!] Backend tidak tersedia setelah {timeout} detik")
        return False
    
    async def check_openapi(self) -> dict:
        """Get OpenAPI spec to understand available endpoints."""
        resp = await self.client.get(f"{self.base_url}/openapi.json")
        return resp.json()
    
    async def submit_task(self, request_data: dict) -> str:
        """Submit a generation task and return task_id."""
        resp = await self.client.post(
            f"{self.base_url}/api/generate",
            json=request_data
        )
        resp.raise_for_status()
        data = resp.json()
        return data["task_id"]
    
    async def wait_for_task(self, task_id: str, timeout: int = 300) -> dict:
        """Wait for task to complete or fail, return final status."""
        print(f"[*] Menunggu task {task_id}...")
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < timeout:
            resp = await self.client.get(f"{self.base_url}/api/status/{task_id}")
            if resp.status_code == 404:
                await asyncio.sleep(5)
                continue
            resp.raise_for_status()
            data = resp.json()
            
            status = data.get("status")
            progress = data.get("progress", 0)
            
            if status != last_status:
                print(f"    Status: {status} (progress: {progress}%)")
                last_status = status
            
            if status in ["completed", "failed"]:
                elapsed = time.time() - start_time
                print(f"[{'+' if status == 'completed' else '!'}] Task {status} setelah {elapsed:.1f} detik")
                return data
            
            await asyncio.sleep(5)
        
        return {"status": "timeout", "task_id": task_id}
    
    async def check_ifc_file(self, task_id: str) -> dict:
        """Check if IFC file was generated."""
        ifc_path = Path(f"/home/nodesemesta/dev/Arsitektur/service/outputs/{task_id}.ifc")
        if ifc_path.exists():
            size = ifc_path.stat().st_size
            print(f"[+] IFC file exists: {ifc_path} ({size} bytes)")
            
            # Analyze IFC content
            try:
                import ifcopenshell
                f = ifcopenshell.open(str(ifc_path))
                products = f.by_type("IfcProduct")
                
                type_counts = {}
                for p in products:
                    t = p.is_a()
                    type_counts[t] = type_counts.get(t, 0) + 1
                
                return {
                    "exists": True,
                    "size": size,
                    "total_products": len(products),
                    "type_counts": type_counts
                }
            except Exception as e:
                return {
                    "exists": True,
                    "size": size,
                    "error": str(e)
                }
        else:
            print(f"[-] IFC file NOT found: {ifc_path}")
            return {"exists": False}
    
    async def run_test(self, name: str, request_data: dict, expected_success: bool = True):
        """Run a single test case."""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        
        try:
            # Submit task
            task_id = await self.submit_task(request_data)
            print(f"[+] Task submitted: {task_id}")
            
            # Wait for completion
            result = await self.wait_for_task(task_id)
            
            # Check IFC
            ifc_result = await self.check_ifc_file(task_id)
            
            # Print summary
            print(f"\n{'='*60}")
            print(f"HASIL TEST: {name}")
            print(f"{'='*60}")
            print(f"Task ID:    {task_id}")
            print(f"Status:     {result.get('status')}")
            print(f"Progress:   {result.get('progress')}%")
            
            if result.get("error_message"):
                print(f"Error:      {result.get('error_message')}")
            
            if result.get("result"):
                print(f"Result:     {json.dumps(result.get('result'), indent=2)[:500]}")
            
            if ifc_result.get("exists"):
                print(f"IFC Size:   {ifc_result.get('size')} bytes")
                print(f"IFC Types:  {ifc_result.get('type_counts')}")
            else:
                print(f"IFC File:   NOT FOUND")
            
            return {
                "test_name": name,
                "success": result.get("status") == "completed",
                "task_id": task_id,
                "result": result,
                "ifc_result": ifc_result
            }
            
        except Exception as e:
            print(f"\n[!] EXCEPTION in test '{name}':")
            print(traceback.format_exc())
            return {
                "test_name": name,
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def close(self):
        await self.client.aclose()


async def main():
    tester = BackendTester()
    
    # Check backend
    if not await tester.wait_for_backend():
        print("[!] Backend tidak tersedia. Jalankan 'make backend' terlebih dahulu.")
        return
    
    # Test 1: Full structured request
    request_full = {
        "prompt": "Rumah minimalis 2 lantai dengan 3 kamar tidur di Bandung",
        "is_structured": True,
        "specification": {
            "project_name": "Rumah Keluarga Bandung",
            "style": "modern",
            "location": {
                "name": "Bandung",
                "country": "Indonesia",
                "latitude": -6.9175,
                "longitude": 107.6191,
                "timezone": "Asia/Jakarta"
            },
            "site": {
                "total_land_area_m2": 150,
                "building_footprint_m2": 80,
                "building_width_m": 8,
                "building_depth_m": 10,
                "orientation": "north",
                "setback_north_m": 3,
                "setback_south_m": 2,
                "setback_east_m": 2,
                "setback_west_m": 2
            },
            "floors": [
                {"floor_number": 1, "height_m": 3.5, "ceiling_height_m": 3.0, "slab_thickness_m": 0.15, "purpose": "residential"},
                {"floor_number": 2, "height_m": 3.2, "ceiling_height_m": 3.0, "slab_thickness_m": 0.15, "purpose": "residential"}
            ],
            "rooms": [
                {"room_type": "living_room", "count": 1, "min_width_m": 4, "min_length_m": 5, "min_area_m2": 20, "preferred_floor": 1},
                {"room_type": "dining_room", "count": 1, "min_width_m": 3.5, "min_length_m": 4, "min_area_m2": 14, "preferred_floor": 1},
                {"room_type": "kitchen", "count": 1, "min_width_m": 3, "min_length_m": 3, "min_area_m2": 9, "preferred_floor": 1},
                {"room_type": "bedroom", "count": 2, "min_width_m": 3, "min_length_m": 3.5, "min_area_m2": 10.5, "preferred_floor": 2},
                {"room_type": "master_bedroom", "count": 1, "min_width_m": 4, "min_length_m": 4.5, "min_area_m2": 18, "preferred_floor": 2},
                {"room_type": "bathroom", "count": 2, "min_width_m": 2, "min_length_m": 2, "min_area_m2": 4, "preferred_floor": 1}
            ],
            "circulation": {"corridor_width_m": 1.2, "staircase_width_m": 1.2},
            "zoning": {"public": ["living_room", "dining_room"], "private": ["bedroom", "master_bedroom"], "service": ["kitchen", "bathroom"]},
            "constraints": {"entrance_position": "front_center", "kitchen_location": "rear", "master_bedroom_location": "rear_corner"}
        }
    }
    
    # Run test
    results = []
    
    result = await tester.run_test("Full Structured Request - Bandung House", request_full)
    results.append(result)
    
    await tester.close()
    
    # Summary
    print(f"\n{'='*60}")
    print("RINGKASAN HASIL TEST")
    print(f"{'='*60}")
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        print(f"  [{status}] {r['test_name']}")
        if not r["success"] and r.get("error"):
            print(f"       Error: {r['error'][:100]}...")
    
    success_count = sum(1 for r in results if r["success"])
    print(f"\nTotal: {success_count}/{len(results)} test berhasil")
    
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)