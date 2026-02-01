"""
Tax document extraction data models.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TaxExtraction(BaseModel):
    """
    Tax document extraction results model.

    Contains the five key fields extracted from tax documents (1040 forms).

    Attributes:
        filing_status: Tax filing status (e.g., Single, Married Filing Jointly)
        w2_wages: Total wages from W-2 forms
        total_deductions: Total deductions claimed
        ira_distributions_total: Total IRA distributions
        capital_gain_or_loss: Total capital gains or losses
    """
    filing_status: Optional[str] = Field(
        None,
        description="Filing status (Single, Married Filing Jointly, etc.)"
    )
    w2_wages: Optional[float] = Field(
        None,
        description="Total W-2 wages",
        ge=0
    )
    total_deductions: Optional[float] = Field(
        None,
        description="Total deductions",
        ge=0
    )
    ira_distributions_total: Optional[float] = Field(
        None,
        description="Total IRA distributions",
        ge=0
    )
    capital_gain_or_loss: Optional[float] = Field(
        None,
        description="Total capital gains or losses (can be negative)"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "filing_status": "Single",
                "w2_wages": 75000.00,
                "total_deductions": 12950.00,
                "ira_distributions_total": 0.00,
                "capital_gain_or_loss": 1500.00
            }
        }
