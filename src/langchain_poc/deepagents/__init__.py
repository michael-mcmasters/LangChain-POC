"""Pattern 2: deepagents.

Expose stream_ask so callers can do `from langchain_poc.deepagents import stream_ask`.

Naming note: this local package shares its name with the installed `deepagents`
LIBRARY. That's fine — Python's absolute imports resolve a bare `from deepagents
import ...` to the top-level library, never to this package (which is only
reachable as `langchain_poc.deepagents`)."""

from langchain_poc.deepagents.agent import stream_ask

__all__ = ["stream_ask"]
