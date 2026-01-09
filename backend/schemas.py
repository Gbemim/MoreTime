"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import List


class GenerateRulesRequest(BaseModel):
    """Request model for generating block rules"""
    description: str = Field(..., min_length=1, description="User's natural language description of websites to block")


class GenerateRulesResponse(BaseModel):
    """Response model containing generated block rules"""
    summary: str = Field(..., description="AI-generated summary of what will be blocked, including 5-10 example websites")


class CheckMetadataRequest(BaseModel):
    """Request to check if website metadata matches a rule"""
    user_description: str = Field(..., description="Original user description/rule")
    metadata: dict = Field(..., description="Website metadata to check")
    url: str = Field(..., description="Website URL")


class CheckMetadataResponse(BaseModel):
    """Response indicating if metadata matches the rule"""
    matches: bool = Field(..., description="Whether the website matches the rule")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str = Field(..., description="Explanation of why it matches or doesn't")

