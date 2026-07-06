### About
A simple Python Langchain application to learn.

### Run project
uv run uvicorn langchain_poc.api:app --reload
Go to http://localhost:8000/ to and you should see {"Hello":"World"}

### Invoke
```ps
Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method Post -ContentType "application/json" -Body '{"message": "What is the current time?"}'
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
