"""Controller - Uses FastAPI and Uvicorn (both are needed)"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from langchain_poc import agent
from langchain_poc.schemas import ChatRequest, ChatResponse

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    reply = agent.ask(req.message)
    return ChatResponse(reply=reply)


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    # Same work as /chat, but instead of waiting for the full reply and returning
    # it in one JSON blob, we hand FastAPI an async generator. FastAPI keeps the
    # HTTP connection open and flushes each chunk to the client as it's produced,
    # so the caller sees the answer appear word-by-word (like ChatGPT typing).
    #
    # media_type="text/plain" keeps this simple to read and test. The common
    # production pattern is Server-Sent Events ("text/event-stream"), where each
    # chunk is framed as "data: <token>\n\n".
    return StreamingResponse(agent.stream_ask(req.message), media_type="text/plain")
