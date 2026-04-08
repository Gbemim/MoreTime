"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Literal, Optional


class GenerateRulesRequest(BaseModel):
    """Request model for generating block rules"""
    description: str = Field(..., min_length=1, description="User's natural language description of websites to block")


class GenerateRulesResponse(BaseModel):
    """Response model containing generated block rules"""
    summary: str = Field(..., description="AI-generated summary of what will be blocked, including 5-10 example websites")


class CheckMetadataRequest(BaseModel):
    """Request to check if website metadata matches a rule"""
    user_description: Optional[str] = Field(
        default=None,
        description="Original user description/rule (legacy fallback)",
    )
    rule_id: Optional[str] = Field(default=None, description="Rule id to evaluate")
    url: str = Field(..., description="Website URL")
    metadata: Optional[dict] = Field(
        default=None,
        description="Optional metadata payload captured client-side",
    )


class CheckMetadataResponse(BaseModel):
    """Response indicating if metadata matches the rule"""
    model_config = ConfigDict(protected_namespaces=())

    matches: bool = Field(..., description="Whether the website matches the rule")
    block: bool = Field(..., description="Canonical backend block decision")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str = Field(..., description="Explanation of why it matches or doesn't")
    reason_code: str = Field(..., description="Short backend reason code for decision")
    decision_id: str = Field(..., description="Unique decision identifier")
    matched_rule_id: Optional[str] = Field(default=None, description="Matched rule id")
    model_name: str = Field(..., description="Model used for this decision")
    evaluated_at: int = Field(..., description="Unix timestamp in milliseconds")


class DurationSchedule(BaseModel):
    type: Literal["duration"]
    durationMinutes: int = Field(..., ge=1)
    startTime: int = Field(..., ge=0)


class DailySchedule(BaseModel):
    type: Literal["daily"]
    daysOfWeek: List[int] = Field(..., min_length=1)
    startTime: str
    endTime: str


class RuleSchedule(BaseModel):
    type: Literal["duration", "daily"]
    durationMinutes: Optional[int] = None
    startTime: int | str
    daysOfWeek: Optional[List[int]] = None
    endTime: Optional[str] = None


class BlockRuleBase(BaseModel):
    userDescription: str = Field(..., min_length=1)
    aiSummary: str = Field(..., min_length=1)
    patterns: List[dict] = Field(default_factory=list)
    schedule: RuleSchedule
    enabled: bool = True


class BlockRule(BlockRuleBase):
    id: str
    createdAt: int


class CreateRuleRequest(BaseModel):
    userDescription: str = Field(..., min_length=1)
    aiSummary: str = Field(..., min_length=1)
    schedule: RuleSchedule


class ToggleRuleRequest(BaseModel):
    enabled: bool


class RulesListResponse(BaseModel):
    rules: List[BlockRule]

