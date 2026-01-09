"""
Configuration management for environment variables
"""

import os
from typing import Optional


def get_anthropic_api_key() -> Optional[str]:
    """
    Get Anthropic API key from environment variable
    
    Returns:
        API key string or None if not set
    """
    return os.getenv("ANTHROPIC_API_KEY")


def get_openai_api_key() -> Optional[str]:
    """
    Get OpenAI API key from environment variable
    
    Returns:
        API key string or None if not set
    """
    return os.getenv("OPENAI_API_KEY")


def require_anthropic_api_key() -> str:
    """
    Get Anthropic API key and raise error if not set
    
    Returns:
        API key string
        
    Raises:
        ValueError: If API key is not set
    """
    api_key = get_anthropic_api_key()
    if not api_key:
        from constants import ERROR_API_KEY_MISSING_ANTHROPIC
        raise ValueError(ERROR_API_KEY_MISSING_ANTHROPIC)
    return api_key


def require_openai_api_key() -> str:
    """
    Get OpenAI API key and raise error if not set
    
    Returns:
        API key string
        
    Raises:
        ValueError: If API key is not set
    """
    api_key = get_openai_api_key()
    if not api_key:
        from constants import ERROR_API_KEY_MISSING_OPENAI
        raise ValueError(ERROR_API_KEY_MISSING_OPENAI)
    return api_key


