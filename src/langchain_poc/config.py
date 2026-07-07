"""Central configuration. Runs once after app starts, the first time this module is imported"""

import logging
import os

from dotenv import load_dotenv

# Configures logging - force=True overrides Uvicorn's default logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    force=True,
)

load_dotenv()

MODEL_NAME = "claude-sonnet-4-6"

# Fail fast if variable is not set - LangChain (ChatAnthropic) reads this values from os.environ just as we're doing here
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file at the project root.")