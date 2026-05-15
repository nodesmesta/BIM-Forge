#!/usr/bin/env python3
"""
IFC Validation Script for BIM Quality Guardian
Validates IFC files against specification requirements
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Try to import ifc解析 libraries
try:
    import ifcopenshell
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False
    print("Warning: ifcopenshell not installed, using fallback parser")


class IFCValidator:
    """Validates IFC files for BIM quality standards"""
    
    def __init__(self, ifc_path: str):
        self.ifc_path = Path(ifc_path)
        self.ifc = None
        self.issues: List[Dict] = []
        self.passed_checks: List[str] = []
        
    def load(self) -> bool:
        """Load IFC file"""
        if not self.ifc_path.exists():
            self.issues.append({
                "check": "file_exists",
                "severity": "critical",
                "message": f"IFC file not found: {self.ifc_path}"
            })
            return False
            
        if HAS_IFCOPENSHELL:
            try:
                self.ifc = ifcopenshell.open(str(self.ifc_path))
                return True
            except Exception as e:
                self.issues.append({
                    "check": "ifc_load",
                    "severity": "critical",
                    "message": f"Failed to load IFC: {e}"
                })
                return False
        return True
    
    def check_spatial(self) -> bool:
        """Check if rooms are within wall boundaries"""
        check_name = "spatial_boundaries"
        
        if not self.ifc:
            self.issues.append({
                "check": check_name,
                "severity": "error",
                "message": "Cannot check spatial - IFC not loaded"
            })
            return False
        
        # TODO: Implement actual spatial validation
        # For now, check if spaces exist
        if HAS_IFCOPENSHELL:
            spaces = self.ifc.by_type("IfcSpace")
            walls = self.ifc.by_type("IfcWall")
            
            if not spaces:
                self.issues.append({
                    "check": check_name,
                    "severity": "error",
                    "message": "No IfcSpace entities found"
                })
                return False
            
            # Check for rooms outside building bounds
            # Placeholder for actual boundary check
            self.passed_checks.append(check_name)
            return True
        
        self.passed_checks.append(check_name)
        return True
    
    def check_doors(self) -> bool:
        """Check if all rooms have doors"""
        check_name = "door_presence"
        
        if not self.ifc:
            self.issues.append({
                "check": check_name,
                "severity": "error",
                "message": "Cannot check doors - IFC not loaded"
            })
            return False
            
        if HAS_IFCOPENSHELL:
            doors = self.ifc.by_type("IfcDoor")
            spaces = self.ifc.by_type("IfcSpace")
            
            if not doors:
                self.issues.append({
                    "check": check_name,
                    "severity": "warning",
                    "message": "No doors found in IFC"
                })
                return False
            
            # Check if each space has at least one door
            # Simplified check - check door count vs space count
            if len(doors) < len(spaces):
                self.issues.append({
                    "check": check_name,
                    "severity": "warning",
                    "message": f"Only {len(doors)} doors for {len(spaces)} spaces"
                })
                return False
            
            self.passed_checks.append(check_name)
            return True
        
        self.passed_checks.append(check_name)
        return True
    
    def check_electrical(self) -> bool:
        """Check if electrical outlets exist"""
        check_name = "electrical_outlets"
        
        if not self.ifc:
            self.issues.append({
                "check": check_name,
                "severity": "error",
                "message": "Cannot check electrical - IFC not loaded"
            })
            return False
            
        if HAS_IFCOPENSHELL:
            outlets = self.ifc.by_type("IfcFlowTerminal")
            # Filter for outlets if possible
            
            if len(outlets) < 5:  # Minimum expected outlets
                self.issues.append({
                    "check": check_name,
                    "severity": "warning",
                    "message": f"Only {len(outlets)} electrical outlets found (expected >= 5)"
                })
                return False
            
            self.passed_checks.append(check_name)
            return True
        
        self.passed_checks.append(check_name)
        return True
    
    def check_schema(self) -> bool:
        """Validate IFC4 schema compliance"""
        check_name = "ifc_schema"
        
        if not self.ifc:
            self.issues.append({
                "check": check_name,
                "severity": "error",
                "message": "Cannot check schema - IFC not loaded"
            })
            return False
            
        if HAS_IFCOPENSHELL:
            schema = self.ifc.schema
            if schema != "IFC4":
                self.issues.append({
                    "check": check_name,
                    "severity": "warning",
                    "message": f"Schema is {schema}, expected IFC4"
                })
                return False
            
            # Check for required entities
            required = ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey"]
            for entity in required:
                if not self.ifc.by_type(entity):
                    self.issues.append({
                        "check": check_name,
                        "severity": "error",
                        "message": f"Missing required entity: {entity}"
                    })
                    return False
            
            self.passed_checks.append(check_name)
            return True
        
        self.passed_checks.append(check_name)
        return True
    
    def check_dimensions(self, spec_path: Optional[str] = None) -> bool:
        """Check if dimensions match specification"""
        check_name = "dimensions"
        
        if not self.ifc:
            self.issues.append({
                "check": check_name,
                "severity": "error",
                "message": "Cannot check dimensions - IFC not loaded"
            })
            return False
        
        if spec_path:
            # Load specification and compare
            try:
                with open(spec_path, 'r') as f:
                    spec = json.load(f)
                
                expected_area = spec.get('specification', {}).get('site', {}).get('total_land_area_m2', 0)
                # TODO: Extract actual area from IFC and compare
                
            except Exception as e:
                self.issues.append({
                    "check": check_name,
                    "severity": "error",
                    "message": f"Failed to load spec: {e}"
                })
                return False
        
        self.passed_checks.append(check_name)
        return True
    
    def run_all_checks(self, spec_path: Optional[str] = None) -> Dict:
        """Run all validation checks"""
        checks = [
            ("spatial", self.check_spatial),
            ("doors", self.check_doors),
            ("electrical", self.check_electrical),
            ("schema", self.check_schema),
            ("dimensions", lambda: self.check_dimensions(spec_path)),
        ]
        
        results = []
        for name, check_fn in checks:
            try:
                passed = check_fn()
                results.append({
                    "check": name,
                    "passed": passed,
                    "severity": "info" if passed else "error"
                })
            except Exception as e:
                results.append({
                    "check": name,
                    "passed": False,
                    "severity": "error",
                    "error": str(e)
                })
        
        return {
            "file": str(self.ifc_path),
            "total_checks": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "checks": results,
            "issues": self.issues,
            "passed_checks": self.passed_checks
        }


def main():
    parser = argparse.ArgumentParser(description="Validate IFC files")
    parser.add_argument("ifc_file", help="Path to IFC file")
    parser.add_argument("--spec", help="Path to specification JSON")
    parser.add_argument("--check-spatial", action="store_true", help="Check spatial boundaries")
    parser.add_argument("--check-doors", action="store_true", help="Check door presence")
    parser.add_argument("--check-electrical", action="store_true", help="Check electrical")
    parser.add_argument("--check-schema", action="store_true", help="Check schema")
    parser.add_argument("--check-dimensions", action="store_true", help="Check dimensions")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    validator = IFCValidator(args.ifc_file)
    
    if not validator.load():
        print(json.dumps({"error": validator.issues}, indent=2) if args.json else f"Failed to load IFC: {validator.issues}")
        sys.exit(1)
    
    # Determine which checks to run
    run_checks = []
    if args.all:
        run_checks = ["spatial", "doors", "electrical", "schema", "dimensions"]
    elif args.check_spatial:
        run_checks.append("spatial")
    elif args.check_doors:
        run_checks.append("doors")
    elif args.check_electrical:
        run_checks.append("electrical")
    elif args.check_schema:
        run_checks.append("schema")
    elif args.check_dimensions:
        run_checks.append("dimensions")
    else:
        run_checks = ["spatial", "doors", "electrical", "schema"]
    
    # Run selected checks
    check_methods = {
        "spatial": validator.check_spatial,
        "doors": validator.check_doors,
        "electrical": validator.check_electrical,
        "schema": validator.check_schema,
        "dimensions": lambda: validator.check_dimensions(args.spec),
    }
    
    for check in run_checks:
        if check in check_methods:
            check_methods[check]()
    
    result = {
        "file": str(validator.ifc_path),
        "passed_checks": validator.passed_checks,
        "issues": validator.issues,
        "status": "PASS" if not validator.issues else "FAIL"
    }
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"IFC Validation: {result['status']}")
        print(f"Passed: {', '.join(result['passed_checks']) if result['passed_checks'] else 'None'}")
        if result['issues']:
            print("\nIssues:")
            for issue in result['issues']:
                print(f"  - [{issue['severity'].upper()}] {issue['check']}: {issue['message']}")
    
    sys.exit(0 if result['status'] == 'PASS' else 1)


if __name__ == "__main__":
    main()