"""
FastAPI backend server for MoreTime extension
Handles LLM integration to generate website blocking rules
"""

import logging
import os
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory (works regardless of cwd, e.g. uvicorn from repo root)
load_dotenv(Path(__file__).resolve().parent / ".env")

from schemas import (
    BlockRule,
    CreateRuleRequest,
    GenerateRulesRequest,
    GenerateRulesResponse,
    CheckMetadataRequest,
    CheckMetadataResponse,
    RulesListResponse,
    ToggleRuleRequest,
)
from llm import generate_block_rules, check_metadata_matches_rule_optimized
from constants import (
    CORS_ALLOW_ORIGINS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    ERROR_EMPTY_DESCRIPTION,
)
from rules_service import create_rule, delete_rule, list_active_rules, list_rules, toggle_rule

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="MoreTime Backend", version="1.0.0")
API_KEY = os.getenv("BACKEND_API_KEY", "")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
_REQUEST_WINDOWS: dict[str, deque[float]] = defaultdict(deque)

# CORS middleware to allow requests from the Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_auth(
    x_api_key: Optional[str],
    x_tenant_id: Optional[str],
) -> str:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing tenant id")
    return x_tenant_id


def get_tenant_id(
    x_api_key: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None),
) -> str:
    return _validate_auth(x_api_key=x_api_key, x_tenant_id=x_tenant_id)


def _enforce_rate_limit(tenant_id: str) -> None:
    now = time.time()
    window_start = now - 60
    window = _REQUEST_WINDOWS[tenant_id]
    while window and window[0] < window_start:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    window.append(now)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or f"req-{int(time.time() * 1000)}"
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.post("/generate-block-rules", response_model=GenerateRulesResponse)
async def generate_block_rules_endpoint(request: GenerateRulesRequest) -> GenerateRulesResponse:
    """
    Generate blocking rules based on user description using LLM
    
    Args:
        request: Request containing user description
        
    Returns:
        GenerateRulesResponse with AI-generated summary
        
    Raises:
        HTTPException: If description is empty or generation fails
    """
    description_preview = request.description[:100] + "..." if len(request.description) > 100 else request.description
    logger.info(f"[API] POST /generate-block-rules - Description: {description_preview}")
    
    if not request.description or not request.description.strip():
        raise HTTPException(status_code=400, detail=ERROR_EMPTY_DESCRIPTION)

    try:
        result = await generate_block_rules(request.description)
        logger.info("[API] Successfully generated rules")
        return result
    except ValueError as e:
        logger.error(f"[API] Validation error generating rules: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Error generating rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating rules: {str(e)}")


@app.get("/rules", response_model=RulesListResponse)
async def get_rules_endpoint(
    active_only: bool = Query(default=False),
    tenant_id: str = Depends(get_tenant_id),
) -> RulesListResponse:
    _enforce_rate_limit(tenant_id)
    rules = list_active_rules(tenant_id) if active_only else list_rules(tenant_id)
    return RulesListResponse(rules=[BlockRule(**rule) for rule in rules])


@app.post("/rules", response_model=BlockRule)
async def create_rule_endpoint(
    request: CreateRuleRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> BlockRule:
    _enforce_rate_limit(tenant_id)
    rule = create_rule(
        tenant_id=tenant_id,
        user_description=request.userDescription.strip(),
        ai_summary=request.aiSummary.strip(),
        schedule=request.schedule.model_dump(),
    )
    return BlockRule(**rule)


@app.patch("/rules/{rule_id}", response_model=BlockRule)
async def toggle_rule_endpoint(
    rule_id: str,
    request: ToggleRuleRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> BlockRule:
    _enforce_rate_limit(tenant_id)
    rule = toggle_rule(tenant_id, rule_id, request.enabled)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return BlockRule(**rule)


@app.delete("/rules/{rule_id}")
async def delete_rule_endpoint(rule_id: str, tenant_id: str = Depends(get_tenant_id)) -> dict:
    _enforce_rate_limit(tenant_id)
    deleted = delete_rule(tenant_id, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True}


@app.post("/check-metadata", response_model=CheckMetadataResponse)
async def check_metadata_endpoint(
    request: CheckMetadataRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> CheckMetadataResponse:
    """
    Check if website metadata matches a blocking rule using hybrid approach
    
    Args:
        request: Request containing user description, metadata, and URL
        
    Returns:
        CheckMetadataResponse with match result, confidence, and reasoning
        
    Raises:
        HTTPException: If metadata check fails
    """
    _enforce_rate_limit(tenant_id)
    logger.info(f"[API] POST /check-metadata - URL: {request.url}")
    
    try:
        user_description = (request.user_description or "").strip()
        matched_rule_id: Optional[str] = request.rule_id

        if request.rule_id and not user_description:
            rules = list_rules(tenant_id)
            matched = next((rule for rule in rules if rule.get("id") == request.rule_id), None)
            if not matched:
                raise HTTPException(status_code=404, detail="Rule not found")
            user_description = str(matched.get("userDescription", "")).strip()

        if not user_description:
            raise HTTPException(status_code=400, detail="Missing user description")

        result = await check_metadata_matches_rule_optimized(
            user_description=user_description,
            url=request.url,
            metadata_override=request.metadata,
        )
        result.matched_rule_id = matched_rule_id
        logger.info(
            f"[API] Result - block: {result.block}, confidence: {result.confidence:.2f}, "
            f"decision_id: {result.decision_id}"
        )
        return result
    except ValueError as e:
        logger.error(f"[API] Validation error checking metadata: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Error checking metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking metadata: {str(e)}")


@app.get("/")
async def root() -> dict:
    """Root endpoint providing API information"""
    return {
        "message": "MoreTime Backend API",
        "version": "1.0.0",
        "endpoints": {
            "generate_rules": "POST /generate-block-rules",
            "rules": "GET/POST /rules",
            "rule_update": "PATCH/DELETE /rules/{rule_id}",
            "check_metadata": "POST /check-metadata",
            "health": "GET /health"
        }
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT)

