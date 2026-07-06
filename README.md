### About
A simple Python Langchain application to learn.

### TODO
- Create Tool with params
- Introduce memory
- Switch to AWS Bedrock

### Run project
uv run uvicorn langchain_poc.api:app --reload
Go to http://localhost:8000/ to and you should see {"Hello":"World"}

### Invoke
Get Time
```ps
Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method Post -ContentType "application/json" -Body '{"message": "What is the current time?"}'
```

Use Math (Notice it calls 2 tools - Multiply and then Add)
```ps
Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method Post -ContentType "application/json" -Body '{"message": "What is 23 times 17, then add 100 to that?"}'
```

### Secrets / API Keys
Uses Anthropic's API key found in my personal Anthropic account. The key is stored in .env.
APIs prompts are charged separately from your Anthropic account (even though it's the same account).
I pre-paid $5. Once credit runs out requests will fail.
Long-term, want to provision AWS Bedrock which also has Opus, along with cheaper models for testing.

### Things I've learned
Lanchain: Provides abstractions such as @tool
LangGraph: The actual agents doing the work

FastAPI and Uvicorn are both needed for API requests (unlike Spring Web or Express which contains all dependnecies)


### Create a project like this
Create new Python Project (with Langchain)
uv init --package my-app                                // Create
cd my-app                                               // CD
uv add fastapi uvicorn                                  // Install FastAPI & Univcorn (both needed for APIs)
In ./src/my_app, create api.py and add this
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"Hello": "World"}
uv run uvicorn my_app.api:app --reload                  // Run project
Go to http://localhost:8000/ to and you should see {"Hello":"World"}