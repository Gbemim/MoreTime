"""
FastAPI backend server for MoreTime extension
Handles LLM integration to generate website blocking rules
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory (works regardless of cwd, e.g. uvicorn from repo root)
load_dotenv(Path(__file__).resolve().parent / ".env")

from schemas import (
    GenerateRulesRequest,
    GenerateRulesResponse,
    CheckMetadataRequest,
    CheckMetadataResponse,
)
from llm import generate_block_rules, check_metadata_matches_rule_optimized
from constants import (
    CORS_ALLOW_ORIGINS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    ERROR_EMPTY_DESCRIPTION,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="MoreTime Backend", version="1.0.0")

# CORS middleware to allow requests from the Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/check-metadata", response_model=CheckMetadataResponse)
async def check_metadata_endpoint(request: CheckMetadataRequest) -> CheckMetadataResponse:
    """
    Check if website metadata matches a blocking rule using hybrid approach
    
    Args:
        request: Request containing user description, metadata, and URL
        
    Returns:
        CheckMetadataResponse with match result, confidence, and reasoning
        
    Raises:
        HTTPException: If metadata check fails
    """
    logger.info(f"[API] POST /check-metadata - URL: {request.url}")
    logger.info(f"[API] User description: {request.user_description}")
    
    try:
        result = await check_metadata_matches_rule_optimized(
            user_description=request.user_description,
            metadata=request.metadata,
            url=request.url
        )
        logger.info(
            f"[API] Result - matches: {result.matches}, "
            f"confidence: {result.confidence:.2f}"
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

