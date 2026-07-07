"""Pydantic models describing the shape of request/response data."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
