"""
Pydantic models for AL Bot data structures.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    """Question answer types."""
    TEXT = "text"
    NUMBER = "number"
    CHOICE = "choice"
    DATE = "date"


class ScriptQuestion(BaseModel):
    """Script question model."""
    id: str
    order: int
    text: str
    type: QuestionType
    choices: Optional[List[str]] = None
    mandatory: bool = True
    weight: int = Field(default=10, ge=0, le=50)
    hot_values: Optional[List[str]] = None


class Script(BaseModel):
    """Script model."""
    id: str
    name: str
    created_by: str
    questions: List[ScriptQuestion]


class LeadSource(str, Enum):
    """Lead source types."""
    TELEGRAM = "telegram"
    SITE = "site"
    UPLOADED = "uploaded"


class LeadStatus(str, Enum):
    """Lead status types."""
    NEW = "new"
    QUALIFIED = "qualified"
    HOT = "hot"
    FOLLOWUP = "followup"
    BOOKED = "booked"


class LeadAnswer(BaseModel):
    """Lead answer model."""
    question_id: str
    value: str


class Lead(BaseModel):
    """Lead model."""
    id: str
    source: LeadSource
    script_id: str
    answers: List[LeadAnswer]
    lead_score: int = 0
    status: LeadStatus = LeadStatus.NEW
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    calendar_event_id: Optional[str] = None
    crm_id: Optional[str] = None


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemAlert(BaseModel):
    """System alert model."""
    id: str
    level: AlertLevel
    message: str
    component: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
