"""
Building code compliance models.
Contains all data structures for regulatory compliance checking.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class ComplianceCategory(str, Enum):
    """Compliance check categories."""
    ACCESSIBILITY = "accessibility"
    FIRE_SAFETY = "fire_safety"
    ZONING = "zoning"
    STRUCTURAL = "structural"
    SANITARY = "sanitary"
    ENERGY = "energy"
    PARKING = "parking"


class ComplianceStatus(str, Enum):
    """Compliance check status."""
    PASS = "PASS"
    FAIL = "FAIL"
    N_A = "N/A"
    PENDING = "PENDING"


class BuildingCode(str, Enum):
    """Indonesian building codes and standards."""
    SNI_03_1733_2002 = "SNI 03-1733-2002"  # Tata cara perancangan lingkungan permukiman
    SNI_03_2459_2001 = "SNI 03-2459-2001"  # Tata cara perancangan ventilasi alami
    SNI_03_6575_2001 = "SNI 03-6575-2001"  # Tata cara perancangan pencahayaan buatan
    SNI_03_6572_2001 = "SNI 03-6572-2001"  # Tata cara perancangan sistem penyalur air hujan
    SNI_03_0239_1991 = "SNI 03-0239-1991"  # Tata cara perhitungan beban rencana
    SNI_03_1729_2002 = "SNI 03-1729-2002"  # Persyaratan beban untuk bangunan gedung
    SNI_03_2847_2002 = "SNI 03-2847-2002"  # Standar beton bertulang
    IMB_REG = "IMB Regulation"  # Izin Mendirikan Bangunan
    KBBI = "KBBI"  # Ketentuan Bangunan Tinggi


class CodeRequirement(BaseModel):
    """Building code requirement definition."""
    code_id: BuildingCode
    regulation_name: str
    requirement_text: str
    category: ComplianceCategory
    minimum_value: Optional[float] = None
    maximum_value: Optional[float] = None
    unit: Optional[str] = None
    description: Optional[str] = None


class ComplianceCheck(BaseModel):
    """Individual compliance check result."""
    requirement: CodeRequirement
    checked_value: float
    status: ComplianceStatus
    notes: Optional[str] = None
    evidence: Optional[str] = None  # Reference to drawing/section
    corrected_value: Optional[float] = None  # If auto-corrected


class ComplianceReport(BaseModel):
    """Complete compliance report for a project."""
    project_id: str
    checks: List[ComplianceCheck] = []
    overall_status: ComplianceStatus = ComplianceStatus.PENDING
    passed_count: int = 0
    failed_count: int = 0
    na_count: int = 0
    recommendations: List[str] = []
    generated_at: Optional[str] = None

    def add_check(self, check: ComplianceCheck):
        """Add a compliance check and update counts."""
        self.checks.append(check)
        self._update_counts()

    def _update_counts(self):
        """Update pass/fail/NA counts."""
        self.passed_count = sum(1 for c in self.checks if c.status == ComplianceStatus.PASS)
        self.failed_count = sum(1 for c in self.checks if c.status == ComplianceStatus.FAIL)
        self.na_count = sum(1 for c in self.checks if c.status == ComplianceStatus.N_A)

        # Update overall status
        if self.failed_count > 0:
            self.overall_status = ComplianceStatus.FAIL
        elif self.passed_count > 0:
            self.overall_status = ComplianceStatus.PASS
        else:
            self.overall_status = ComplianceStatus.PENDING

    def get_summary(self) -> Dict:
        """Get compliance summary as dictionary."""
        return {
            "project_id": self.project_id,
            "overall_status": self.overall_status.value,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "not_applicable": self.na_count,
            "total_checks": len(self.checks),
            "pass_rate": f"{(self.passed_count / len(self.checks) * 100) if self.checks else 0:.1f}%"
        }
