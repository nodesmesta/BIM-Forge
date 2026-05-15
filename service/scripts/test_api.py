#!/usr/bin/env python3
"""
API Test Script for BIM Quality Guardian
Tests all API endpoints with sample data
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: float = 0
    details: Optional[Dict] = None


class APITester:
    """Tests BIM API endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.results: List[TestResult] = []
        self.task_id: Optional[str] = None
    
    def _request(self, method: str, path: str, **kwargs) -> tuple:
        """Make HTTP request and return (success, response_data, duration)"""
        url = f"{self.base_url}{path}"
        start = time.time()
        
        try:
            response = requests.request(method, url, **kwargs, timeout=60)
            duration = (time.time() - start) * 1000
            
            try:
                data = response.json()
            except:
                data = {"raw": response.text}
            
            return response.status_code < 400, data, duration
            
        except requests.exceptions.Timeout:
            return False, {"error": "Request timeout"}, (time.time() - start) * 1000
        except Exception as e:
            return False, {"error": str(e)}, (time.time() - start) * 1000
    
    def test_health(self) -> TestResult:
        """Test API health endpoint"""
        success, data, duration = self._request("GET", "/api/health")
        
        return TestResult(
            name="health_check",
            passed=success,
            message="API healthy" if success else f"API unhealthy: {data.get('error', 'unknown')}",
            duration_ms=duration
        )
    
    def test_docs(self) -> TestResult:
        """Test Swagger docs availability"""
        success, data, duration = self._request("GET", "/docs")
        
        passed = success and "swagger" in str(data).lower()
        
        return TestResult(
            name="swagger_docs",
            passed=passed,
            message="Swagger docs available" if passed else "Swagger docs not accessible",
            duration_ms=duration
        )
    
    def test_tasks_list(self) -> TestResult:
        """Test tasks list endpoint"""
        success, data, duration = self._request("GET", "/api/tasks")
        
        passed = success and isinstance(data, dict) and "tasks" in data
        
        return TestResult(
            name="tasks_list",
            passed=passed,
            message=f"Tasks endpoint OK ({data.get('total', 0)} tasks)" if passed else f"Failed: {data}",
            duration_ms=duration,
            details={"total_tasks": data.get("total", 0)}
        )
    
    def test_task_generation(self, spec_path: Optional[str] = None) -> TestResult:
        """Test task generation endpoint"""
        # Sample specification
        spec = {
            "prompt": "Test rumah minimalis",
            "is_structured": True,
            "specification": {
                "project_name": "Test Guardian House",
                "style": "minimalist",
                "location": {
                    "name": "Bandung",
                    "country": "Indonesia",
                    "latitude": -6.9175,
                    "longitude": 107.6191,
                    "timezone": "Asia/Jakarta"
                },
                "site": {
                    "total_land_area_m2": 100,
                    "building_footprint_m2": 60,
                    "building_width_m": 8,
                    "building_depth_m": 7.5,
                    "orientation": "north",
                    "setback_north_m": 2,
                    "setback_south_m": 2,
                    "setback_east_m": 1.5,
                    "setback_west_m": 1.5
                },
                "floors": [
                    {"floor_number": 1, "height_m": 3.5, "ceiling_height_m": 3.0, "purpose": "residential"}
                ],
                "rooms": [
                    {"room_type": "living_room", "count": 1, "min_area_m2": 15, "preferred_floor": 1},
                    {"room_type": "bedroom", "count": 1, "min_area_m2": 10, "preferred_floor": 1},
                    {"room_type": "bathroom", "count": 1, "min_area_m2": 4, "preferred_floor": 1}
                ]
            }
        }
        
        success, data, duration = self._request(
            "POST", "/api/generate",
            json=spec,
            headers={"Content-Type": "application/json"}
        )
        
        if success and "task_id" in data:
            self.task_id = data["task_id"]
        
        return TestResult(
            name="task_generation",
            passed=success and "task_id" in data,
            message=f"Task created: {data.get('task_id', 'N/A')}" if success else f"Failed: {data}",
            duration_ms=duration,
            details={"task_id": data.get("task_id")}
        )
    
    def test_task_status(self, task_id: str) -> TestResult:
        """Test getting task status"""
        success, data, duration = self._request("GET", f"/api/tasks")
        
        if success:
            tasks = data.get("tasks", [])
            task = next((t for t in tasks if t["id"] == task_id), None)
            status = task["status"] if task else "not_found"
        else:
            status = "error"
        
        return TestResult(
            name="task_status",
            passed=success,
            message=f"Task status: {status}",
            duration_ms=duration,
            details={"status": status}
        )
    
    def test_gallery(self) -> TestResult:
        """Test gallery endpoint"""
        success, data, duration = self._request("GET", "/api/gallery")
        
        if success:
            # Handle both list and dict response
            if isinstance(data, list):
                items = data
            else:
                items = data.get("items", [])
        else:
            items = []
        
        return TestResult(
            name="gallery",
            passed=success,
            message=f"Gallery OK ({len(items)} items)" if success else f"Failed: {data}",
            duration_ms=duration,
            details={"item_count": len(items)}
        )
    
    def test_websocket(self) -> TestResult:
        """Test WebSocket connection"""
        if not self.task_id:
            return TestResult(
                name="websocket",
                passed=False,
                message="Skipped - no task ID available"
            )
        
        try:
            import websocket
            
            ws_url = self.base_url.replace("http", "ws") + f"/api/ws/{self.task_id}"
            ws = websocket.create_connection(ws_url, timeout=10)
            ws.close()
            
            return TestResult(
                name="websocket",
                passed=True,
                message="WebSocket connected successfully"
            )
        except ImportError:
            return TestResult(
                name="websocket",
                passed=False,
                message="Skipped - websocket-client not installed"
            )
        except Exception as e:
            return TestResult(
                name="websocket",
                passed=False,
                message=f"WebSocket failed: {e}"
            )
    
    def run_full_test(self, wait_for_task: bool = True) -> Dict:
        """Run full API test suite"""
        tests = [
            self.test_health,
            self.test_docs,
            self.test_tasks_list,
            self.test_gallery,
            lambda: self.test_task_generation(),
        ]
        
        for test_fn in tests:
            result = test_fn()
            self.results.append(result)
        
        # Wait for task to complete if generation succeeded
        if wait_for_task and self.task_id:
            max_wait = 120  # 2 minutes
            waited = 0
            
            while waited < max_wait:
                time.sleep(5)
                waited += 5
                
                result = self.test_task_status(self.task_id)
                if result.details and result.details.get("status") in ["completed", "failed", "approved"]:
                    self.results.append(result)
                    break
                
                if waited >= max_wait:
                    self.results.append(TestResult(
                        name="task_completion",
                        passed=False,
                        message=f"Task still running after {max_wait}s"
                    ))
        
        return self.get_summary()
    
    def get_summary(self) -> Dict:
        """Get test summary"""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total_duration = sum(r.duration_ms for r in self.results)
        
        return {
            "base_url": self.base_url,
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/len(self.results)*100):.1f}%" if self.results else "N/A",
            "total_duration_ms": round(total_duration, 2),
            "task_id": self.task_id,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration_ms": round(r.duration_ms, 2),
                    "details": r.details
                }
                for r in self.results
            ]
        }


def main():
    parser = argparse.ArgumentParser(description="Test BIM API")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--health", action="store_true", help="Run health check only")
    parser.add_argument("--generate", action="store_true", help="Test task generation")
    parser.add_argument("--full", action="store_true", help="Run full test suite")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--wait", type=int, default=0, help="Wait N seconds for task completion")
    
    args = parser.parse_args()
    
    if not HAS_REQUESTS:
        print("Error: requests library required. Install with: pip install requests")
        sys.exit(1)
    
    tester = APITester(args.url)
    
    if args.health:
        result = tester.test_health()
        print(json.dumps({"test": result.__dict__}, indent=2) if args.json else f"Health: {result.message}")
        sys.exit(0 if result.passed else 1)
    elif args.generate:
        result = tester.test_task_generation()
        print(json.dumps({"test": result.__dict__}, indent=2) if args.json else f"Generate: {result.message}")
        sys.exit(0 if result.passed else 1)
    else:
        summary = tester.run_full_test(wait_for_task=args.wait > 0)
        
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"\n{'='*50}")
            print(f"API Test Summary: {summary['base_url']}")
            print(f"{'='*50}")
            print(f"Total: {summary['total_tests']} | Passed: {summary['passed']} | Failed: {summary['failed']}")
            print(f"Pass Rate: {summary['pass_rate']}")
            print(f"Duration: {summary['total_duration_ms']}ms")
            print(f"Task ID: {summary['task_id'] or 'N/A'}")
            print(f"\nResults:")
            for r in summary['results']:
                icon = "✓" if r['passed'] else "✗"
                print(f"  {icon} {r['name']}: {r['message']} ({r['duration_ms']}ms)")
        
        sys.exit(0 if summary.get('failed', 0) == 0 else 1)


if __name__ == "__main__":
    main()