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