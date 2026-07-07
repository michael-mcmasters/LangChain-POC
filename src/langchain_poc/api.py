"""Controller - Uses FastAPI and Uvicorn (both are needed)"""

import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from langchain_poc import agent
from langchain_poc.schemas import ChatRequest

app = FastAPI()


@app.get("/")
def hello_world():
    return {"Hello": "World"}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    # Wrapper that calls agent.stream_ask() and handles stream events
    async def event_stream():
        async for event in agent.stream_ask(req.message, req.thread_id):
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
