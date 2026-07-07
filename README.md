### About
A simple Python Langchain application to learn.

### TODO
- Introduce memory
- Use multiple agents and an orchestrator
- Agent Harness?
- Switch to AWS Bedrock

### Run project
uv run uvicorn langchain_poc.api:app --reload
Go to http://localhost:8000/ to and you should see {"Hello":"World"}

### Invoke
(Commands are on Windows - Use pwsh (not powershell) for syntax to work.)

Get Time
```ps
curl.exe -N -X POST "http://localhost:8000/chat/stream" -H "Content-Type: application/json" -d '{"message": "What is the current time?"}'
```

Use Math (Notice the LLLM calls 2 tools - Multiply and then Add)
```ps
curl.exe -N -X POST "http://localhost:8000/chat/stream" -H "Content-Type: application/json" -d '{"message": "What is 23 times 17, then add 100 to that?"}'
```

### Logs
Making this request:
  curl.exe -N -X POST "http://localhost:8000/chat/stream" -H "Content-Type: application/json" -d '{"message": "What is the current time?"}'

Makes these logs appear:
```
INFO:     127.0.0.1:49758 - "POST /chat/stream HTTP/1.1" 200 OK
16:17:26  INFO    langchain_poc.agent | USER asked (stream): What is 23 times 17, then add 100 to that?
16:17:27  INFO    httpx | HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
16:17:28  INFO    langchain_poc.agent |   AIMessage -> calling tool multiply({'a': 23, 'b': 17})
16:17:28  INFO    langchain_poc.tools | tool: multiply(23.0, 17.0)
16:17:28  INFO    langchain_poc.agent |   ToolMessage: 391.0
16:17:30  INFO    httpx | HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
16:17:31  INFO    langchain_poc.agent |   AIMessage -> calling tool add({'a': 391, 'b': 100})
16:17:31  INFO    langchain_poc.tools | tool: add(391.0, 100.0)
16:17:31  INFO    langchain_poc.agent |   ToolMessage: 491.0
16:17:32  INFO    httpx | HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
16:17:33  INFO    langchain_poc.agent |   AIMessage: Here's the breakdown:
- **23 × 17 = 391**
- **391 + 100 = 491**

The final answer is **491**!
16:17:33  INFO    langchain_poc.agent | FINAL reply: I'll start by multiplying 23 × 17, then add 100 to the result. Let me kick off the multiplication first!391.023 × 17 = 391. Now let me add 100 to that!491.0Here's the breakdown:
- **23 × 17 = 391**
- **391 + 100 = 491**

The final answer is **491**!
```

When we invoke the agent, we pass `stream_mode=["updates", "messages"]`, telling it to give us these response types"
- `Messages`: The tokens (text) the LLM API responds with. We stream these tokens back to the user as they come in.
- `Updates`: Status updated from the LLM such as AIMessage and ToolMessage
  - `AIMessage`: A full message from the LLM before it makes another LLM call. (Usually make another LLM call after invoking a tool to use the response)
    - Note for Streams, this isn't the chunked response to the user. This is the complete response before the LLM moves to the next step.
  - `ToolMessage`: This is *always* the Tool's (function's) response. So the LLM calling `add(2 + 2)` will result in `ToolMessage: 4`. It will not show logs we put inside our function
    - Logs starting with "tool: " are our own logs that appear at the time the Tool function runs. These do not come from the agent `updates` object. Good idea to use request-ids so updates and our own logs are all grouped together instead of being intermangled with other user requests


### Secrets / API Keys
Uses Anthropic's API key found in my personal Anthropic account. The key is stored in .env.
APIs prompts are charged separately from your Anthropic account (even though it's the same account).
I pre-paid $5. Once credit runs out requests will fail.
Long-term, want to provision AWS Bedrock which also has Opus, along with cheaper models for testing.

### Things to know for future projects (what I've learned)

### Things I've learned - What I want to remember next time

### Things I've learned
Lanchain: Provides abstractions such as @tool
LangGraph: The actual agents doing the work. The ReAct model (Reason + Act) which is calling a Tool, then calling the LLM, then calling another Tool.

For Tools, the docstring inside the function is for the agent to know when to run them. It's not 100% for humans.

FastAPI and Uvicorn are both needed for API requests (unlike Spring Web or Express which contains all dependnecies)


### Hot to create another Python / Langchain project like this
- Create new Python Project (with Langchain)
- uv init --package my-app                                // Create
- cd my-app                                               // CD
- uv add fastapi uvicorn                                  // Install FastAPI & Univcorn (both needed for APIs)
- In ./src/my_app, create api.py and add this
```
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"Hello": "World"}
uv run uvicorn my_app.api:app --reload                  // Run project
```
- Go to http://localhost:8000/ to and you should see {"Hello":"World"}