"""
Embedding utilities for semantic similarity
"""

import asyncio
import logging
from typing import List

import numpy as np
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from config import require_openai_api_key
from constants import OPENAI_EMBEDDING_MODEL

logger = logging.getLogger(__name__)


async def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector for text using OpenAI
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector as list of floats
        
    Raises:
        ValueError: If API key is not set or embedding fails
    """
    api_key = require_openai_api_key()
    
    client = OpenAIEmbeddings(
        model=OPENAI_EMBEDDING_MODEL,
        api_key=SecretStr(api_key),  # type: ignore[arg-type]
    )
    try:
        return await asyncio.to_thread(client.embed_query, text)
    except Exception as e:
        logger.error(f"Failed to get embedding: {e}")
        raise ValueError(f"Failed to get embedding: {str(e)}") from e


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score between 0 and 1
    """
    arr1 = np.array(vec1)
    arr2 = np.array(vec2)
    return float(np.dot(arr1, arr2) / (np.linalg.norm(arr1) * np.linalg.norm(arr2)))

