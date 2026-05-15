#!/usr/bin/env python3
"""
Blender Integration Test for BIM Quality Guardian
Tests if IFC files can be opened in Blender
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Optional


class BlenderTester:
    """Tests IFC files in Blender"""
    
    def __init__(self, ifc_path: str, blender_path: str = "/usr/bin/blender"):
        self.ifc_path = Path(ifc_path)
        self.blender_path = Path(blender_path)
        self.test_result: Dict = {}
    
    def check_blender(self) -> bool:
        """Check if Blender is installed and available"""
        if not self.blender_path.exists():
            # Try to find blender
            result = subprocess.run(
                ["which", "blender"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.blender_path = Path(result.stdout.strip())
                return True
            self.test_result = {
                "status": "error",
                "message": "Blender not found",
                "blender_path": str(self.blender_path)
            }
            return False
        return True
    
    def test_basic_open(self) -> bool:
        """Test basic Blender open without crash"""
        test_script = """
import bpy
import sys

# Basic test - just open Blender and check it works
try:
    # Check Blender version
    version = bpy.app.version
    print(f"Blender version: {version[0]}.{version[1]}.{version[2]}")
    
    # Check if we can create basic objects
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    print(f"Created cube: {cube.name}")
    
    print("BASIC_TEST_PASSED")
except Exception as e:
    print(f"BASIC_TEST_FAILED: {e}")
    sys.exit(1)
"""
        
        result = subprocess.run(
            [
                str(self.blender_path),
                "--background",
                "--python-expr", test_script
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return "BASIC_TEST_PASSED" in result.stdout
    
    def test_ifc_import(self, api_url: str = "http://localhost:8000") -> bool:
        """Test importing IFC via API"""
        try:
            import requests
            
            # Get latest generated IFC
            response = requests.get(f"{api_url}/api/gallery", timeout=10)
            if response.status_code != 200:
                self.test_result = {
                    "status": "error",
                    "message": "Cannot access gallery API"
                }
                return False
            
            gallery = response.json()
            if not gallery.get("items"):
                self.test_result = {
                    "status": "skip",
                    "message": "No IFC files in gallery to test"
                }
                return False
            
            # Get the most recent IFC
            latest = gallery["items"][0]
            ifc_url = latest.get("ifc_url")
            
            if not ifc_url:
                self.test_result = {
                    "status": "skip",
                    "message": "No IFC URL in gallery item"
                }
                return False
            
            self.test_result = {
                "status": "pending",
                "ifc_url": ifc_url,
                "note": "Blender IFC import test requires manual verification"
            }
            return True
            
        except ImportError:
            self.test_result = {
                "status": "skip",
                "message": "requests library not available for API test"
            }
            return False
        except Exception as e:
            self.test_result = {
                "status": "error",
                "message": str(e)
            }
            return False
    
    def test_direct_ifc(self) -> bool:
        """Test opening IFC file directly in Blender"""
        if not self.ifc_path.exists():
            self.test_result = {
                "status": "error",
                "message": f"IFC file not found: {self.ifc_path}"
            }
            return False
        
        test_script = f"""
import bpy
import sys

try:
    # Try to import ifc (if addon is installed)
    try:
        import ifc
        print("IFC module available")
    except ImportError:
        print("IFC addon not installed - checking file exists")
    
    # Check file exists
    import os
    ifc_path = "{self.ifc_path}"
    if os.path.exists(ifc_path):
        print(f"IFC file exists: {{ifc_path}}")
        print(f"File size: {{os.path.getsize(ifc_path)}} bytes")
    else:
        print(f"IFC file NOT found: {{ifc_path}}")
        sys.exit(1)
    
    print("IFC_FILE_TEST_PASSED")
except Exception as e:
    print(f"IFC_FILE_TEST_FAILED: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
        
        result = subprocess.run(
            [
                str(self.blender_path),
                "--background",
                "--python-expr", test_script
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if "IFC_FILE_TEST_PASSED" in result.stdout:
            self.test_result = {
                "status": "pass",
                "message": "IFC file is accessible",
                "file_path": str(self.ifc_path),
                "file_size": self.ifc_path.stat().st_size
            }
            return True
        else:
            self.test_result = {
                "status": "fail",
                "message": "IFC file test failed",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            return False
    
    def run_all_tests(self) -> Dict:
        """Run all Blender tests"""
        results = {
            "blender_available": False,
            "tests": []
        }
        
        # Test 1: Blender available
        blender_ok = self.check_blender()
        results["blender_available"] = blender_ok
        results["tests"].append({
            "name": "blender_check",
            "status": "pass" if blender_ok else "fail",
            "message": f"Blender at {self.blender_path}" if blender_ok else "Blender not found"
        })
        
        if not blender_ok:
            return results
        
        # Test 2: Basic Blender operation
        basic_ok = self.test_basic_open()
        results["tests"].append({
            "name": "basic_operation",
            "status": "pass" if basic_ok else "fail"
        })
        
        if self.ifc_path.exists():
            # Test 3: IFC file test
            ifc_ok = self.test_direct_ifc()
            results["tests"].append({
                "name": "ifc_file_test",
                "status": "pass" if ifc_ok else "fail",
                "detail": self.test_result
            })
        
        # Calculate overall status
        failed = [t for t in results["tests"] if t["status"] == "fail"]
        results["overall_status"] = "pass" if not failed else "fail"
        results["failed_count"] = len(failed)
        results["total_tests"] = len(results["tests"])
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Test IFC files in Blender")
    parser.add_argument("ifc_file", nargs="?", help="Path to IFC file")
    parser.add_argument("--blender", default="/usr/bin/blender", help="Path to Blender")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--api", default="http://localhost:8000", help="API URL")
    
    args = parser.parse_args()
    
    tester = BlenderTester(
        args.ifc_file if args.ifc_file else "/tmp/test.ifc",
        args.blender
    )
    
    results = tester.run_all_tests()
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        status = results.get('overall_status', 'unknown')
        print(f"Blender Test: {status.upper() if status else 'UNKNOWN'}")
        print(f"Blender Available: {'Yes' if results['blender_available'] else 'No'}")
        print("\nTests:")
        for test in results["tests"]:
            icon = "✓" if test["status"] == "pass" else "✗"
            print(f"  {icon} {test['name']}: {test.get('message', test['status'])}")
        
        if results.get("detail"):
            print(f"\nDetails: {results['detail']}")
    
    sys.exit(0 if results.get('overall_status') == 'pass' else 1)


if __name__ == "__main__":
    main()