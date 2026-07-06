from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel

# Reads ANTHROPIC_API_KEY from .env into the environment before we build the model.
load_dotenv()

app = FastAPI()

# The LLM client. It picks up ANTHROPIC_API_KEY from the environment automatically.
model = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=1024)


# Defines the shape of the JSON body clients must POST: {"message": "..."}.
class ChatRequest(BaseModel):
    message: str


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/chat")
def chat(req: ChatRequest):
    # .invoke sends the message to Claude and blocks until the full reply comes back.
    response = model.invoke(req.message)
    return {"reply": response.content}