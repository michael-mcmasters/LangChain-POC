"""Pydantic models describing the shape of request/response data."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str                    # User Message
    thread_id: str                  # ID for the conversation - Used by LangChain to remember conversation history / updates
