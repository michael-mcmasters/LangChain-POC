### About
A simple Python Langchain application to learn.

### ToDo List
- ~~Tools~~
- ~~Memory~~
- ~~Use Streams instead of POST~~
- ~~Understand Loops~~
- ~~Understand Agent Harness~~
- ~~Use Multiple Agents - Agents-as-tools~~
- ~~Use Multiple Agents - Deepagents~~
- ~~Skills~~
- Switch to AWS Bedrock

### Run project
```pwsh
uv run uvicorn langchain_poc.api:app --reload
```
Go to http://localhost:8000/ to and you should see {"Hello":"World"}

### Invoke
Things to know
- Example commands are on Windows pwsh (not powershell) - If they don't work enter `pwsh` first to use Powershell 7+
- thread_id is your conversation history. To "start a new chat" change it to another value.

Agent-as-tool - Get Time
```pwsh
curl.exe -N -X POST "http://localhost:8000/chat/agent-as-tool" -H "Content-Type: application/json" -d '{"message": "What is the current time?", "thread_id": "ABC"}'
```

Agent-as-tool - Use Math & returns result as ascii-art using skill
```pwsh
curl.exe -N -X POST "http://localhost:8000/chat/agent-as-tool" -H "Content-Type: application/json" -d '{"message": "What is 23 times 17, then add 100 to that?", "thread_id": "ABC"}'
```

Deepagents - Use Math & returns result as ascii-art using skill
```pwsh
curl.exe -N -X POST "http://localhost:8000/chat/deepagents" -H "Content-Type: application/json" -d '{"message": "What is 23 times 17, then add 100 to that?", "thread_id": "ABC"}'
```

### Logs
Making this request:
  curl.exe -N -X POST "http://localhost:8000/chat/agent-as-tool" -H "Content-Type: application/json" -d '{"message": "What is the current time?"}'

Makes these logs appear:
```
INFO:     127.0.0.1:49758 - "POST /chat/agent-as-tool HTTP/1.1" 200 OK
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


### For Future Projects - (Things I've Learned)
- Lanchain: Provides abstractions such as @tool
- LangGraph: The actual agents doing the work. The ReAct model (Reason + Act) which is calling a Tool, then calling the LLM, then calling another Tool.
- Checkpointer: Enables the server to "remember" the existing conversation... Client passes a thread_id. Server (this) stores conversation and updates in a map the thread_id points to. When the client makes a 2nd request, it passes the thread_id, and the server remembers the full conversation history and context.
  - If you restart the app, this state is gone. To persist, you can save to a database.
  - In a real scenario, you should validate the thread_id so that bad actor can't mock it
  - Setting my name with thread_id ABC
    ```
    PS C:\Users\micha\dev\projects\2026\langchain-poc> curl.exe -N -X POST "http://localhost:8000/chat/agent-as-tool" -H "Content-Type: application/json" -d '{"message": "My name is Michael. Please remember it.", "thread_id": "ABC"}'
    Got it, **Michael**! I'll remember your name throughout our conversation. How can I help you today?
    ```
  - Asking my name with thread_id ABC
    ```
    PS C:\Users\micha\dev\projects\2026\langchain-poc> curl.exe -N -X POST "http://localhost:8000/chat/agent-as-tool" -H "Content-Type: application/json" -d '{"message": "What is my name?", "thread_id": "ABC"}'
    Your name is **Michael**! 😊 Is there anything else I can help you with?
    ```
  - Asking my name with no thread_id
    ```
    PS C:\Users\micha\dev\projects\2026\langchain-poc> curl.exe -N -X POST "http://localhost:8000/chat/agent-as-tool" -H "Content-Type: application/json" -d '{"message": "What is my name?"}'
    I don't have access to any personal information about you, so I don't know your name. You're welcome to tell me, and I'll use it in our conversation! 😊
    ```
- Agent Orchestration options:
  - agents-as-tools:
    - (See below for example code)
    - You specify the agents and their tools (via Python functions and @tool annotation)
    - Has its own context so parent agent's context doesn't get bloated - By default, this agent's context starts fresh next time it's called
    - Parent agent only see this agent's response (similar to Tools returning a response) - Doesn't see its logic, context, anything
      - This means you can't stream subagent responses to the user - If you want that, use supervisor graph (below)
  - deepagents:
    - (See below for example code)
    - Similar to agents-as-tools (above points are true for deepagents as well) - But abstracts some of the logic
    - "Batteries included agents" - Meaning they have additional built-in tools such as write-todos to plan multiple steps, read_file, and write_file
  - supervisor graph:
    - (No example code for this one)
    - Agents are peers, route around asupervisor, share context
    - Benefit, you can stream all agent's responses to the user
    - May be more effecient since they share context, but more expensive
- Loops and Harnesses
  - (Mostly buzzwords that blew up in 2026 for behaviours that LangGraph has provided for a while. "Loop Engineering" / "Harness Engineering" replacing "Prompt Engineering")
  - Loop: Model -> tool call -> feed back to model -> tool call -> etc until done
    - (All the logic occuring when my API is called is a loop)
  - Harness: Everything around the agents - System prompt, tools, guardrails, etc
    - (The Agent Orchestration options (above) are the harness)


For Tools, the docstring inside the function is for the agent to know when to run them. It's not 100% for humans.

FastAPI and Uvicorn are both needed for API requests (unlike Spring Web or Express which contains all dependnecies)


### How to use: agents-as-tools
```
# Create math agent
math_agent = create_agent(
    model,
    tools=[add, multiply],
    system_prompt="""You're an expert at math"""
)

# Expose math agent as a tool
@tool
async def math_specialist(question: str) -> str:
    """Use this tool when you need a math agent"""      # docstring is not for us - Tells orchestrator when to use this tool
    return await _run_specialist(math_agent, question)

# Create orchestrator agent - Give it access to tool so it can delegate to math_agent
orchestrator_agent = create_agent(
    model,
    tools=[math_specialist],
    system_prompt="""You're an orchestrator. Answer simple questions or delegate to subagents if necessary""",
)

# Invoke orchestrator agent and it will do the rest: agent.astream( ... )
```


### How to use: deepagents
First install them:
```pwsh
uv add deepagents
```

```
# Create math subagent
math_subagent = {
    "name": "math-agent",
    "description": "Handles simple math equations",
    "system_prompt": """You're an expert at math""",
    "tools": [add, multiply],
}

# Create orchestrator agent - Give it access to math subagent
orchestrator_agent = create_deep_agent(
    model=model,
    tools=[], # Good idea to give orchestrator agents no tools of their own - subagents handle which keeps context low (as it's orchestrator only sees their output)
    system_prompt="""You're an orchestrator. Answer simple questions or delegate to subagents if necessary"""
    subagents=[math_subagent],
)

# Invoke orchestrator agent and it will do the rest: agent.astream( ... )
```


### How to create another Python / Langchain project like this
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
```
- uv run uvicorn my_app.api:app --reload                  // Run project
- Go to http://localhost:8000/ to and you should see {"Hello":"World"}