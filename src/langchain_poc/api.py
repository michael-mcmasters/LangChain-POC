"""Controller - Uses FastAPI and Uvicorn (both are needed)"""

from fastapi import FastAPI

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
