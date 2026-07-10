"""Pattern 1: agents-as-tools.

Expose stream_ask so callers can do `from langchain_poc.agent_as_tool import stream_ask`."""

from langchain_poc.agent_as_tool.agent import stream_ask

__all__ = ["stream_ask"]
