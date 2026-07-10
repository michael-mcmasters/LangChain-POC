"""Controller - Uses FastAPI and Uvicorn (both are needed)."""

import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from langchain_poc import agent_as_tool, deepagents
from langchain_poc.schemas import ChatRequest

app = FastAPI()


@app.post("/chat/agent-as-tool")
async def chat_agent_as_tool(req: ChatRequest):
    return _stream(agent_as_tool.stream_ask(req.message, req.thread_id))


@app.post("/chat/deepagents")
async def chat_deepagents(req: ChatRequest):
    return _stream(deepagents.stream_ask(req.message, req.thread_id))


def _stream(events) -> StreamingResponse:
    """Wrap an async event generator (from a package's stream_ask) as SSE.

    Shared by both endpoints — the only thing that differs between them are events they produce"""
    async def event_stream():
        async for event in events:
            yield f"data: {json.dumps(event)}\n\n"

        # Once stream is complete, set [DONE] so client knows
        yield "data: [DONE]\n\n"

    # Above wrapper is passed here. This initiates the job
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        # no-cache: don't let a proxy/browser cache a live stream.
        # X-Accel-Buffering: tell nginx (if it's ever in front) not to buffer it.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
