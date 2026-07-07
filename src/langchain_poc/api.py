"""Controller - Uses FastAPI and Uvicorn (both are needed)"""

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
    # media_type="text/plain" keeps this simple to read and test. The common
    # production pattern is Server-Sent Events ("text/event-stream"), where each
    # chunk is framed as "data: <token>\n\n".
    return StreamingResponse(agent.stream_ask(req.message), media_type="text/plain")
