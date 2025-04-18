# app/models.py
from typing import Optional, List
from pydantic import BaseModel, Field

class MedicalResponse(BaseModel):
    """Schema for medical response."""
    diagnosis: Optional[str] = Field(None, description="Potential diagnosis based on symptoms")
    recommendations: Optional[List[str]] = Field(None, description="Medical recommendations and advice")
    severity: Optional[str] = Field(None, description="Severity level of the condition (Low, Medium, High)")
    follow_up: Optional[str] = Field(None, description="Follow-up recommendations")

class ThoughtProcess(BaseModel):
    """Schema for agent thought process."""
    thought: str
    action: Optional[str] = None
    action_input: Optional[str] = None
    answer: Optional[str] = None
