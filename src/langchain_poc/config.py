"""Central configuration. Loads .env once for the whole app."""

import logging
import os

from dotenv import load_dotenv

# Configure logging once for the whole app. force=True ensures our format wins
# even though uvicorn also sets up logging. INFO shows our messages; DEBUG would
# add LangChain/HTTP internals.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    force=True,
)

# Runs the first time ANY module imports `config`. Python caches modules after
# their first import, so this executes exactly once per process — before any
# other module reads the environment.
load_dotenv()

# Fail fast at startup with a clear message, instead of a confusing 500 mid-request.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file at the project root.")

# One place to change the model for the whole app.
MODEL_NAME = "claude-sonnet-4-6"
