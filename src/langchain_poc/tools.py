"""
# @tool allows the Agent to call the function
# The docstring tells the agent when to use it - It's not a comment for humans
# For functions with params, uses param types to know what words from the user prompt to pass to the function
"""

import logging
from datetime import datetime

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_current_time() -> str:
    """Return the current date and time. Use this whenever the user asks what
    time or date it is, since you cannot know the current time on your own."""
    logger.info("(Tool Log): get_current_time()")
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def add(a: float, b: float) -> float:
    """Add two numbers and return the result. Use this for any addition."""
    logger.info(f"(Tool Log): add({a}, {b})")
    return a + b


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the result. Use this for any multiplication."""
    logger.info(f"(Tool Log): multiply({a}, {b})")
    return a * b
