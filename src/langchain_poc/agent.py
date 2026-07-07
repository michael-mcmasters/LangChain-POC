"""The AI layer: builds a tool-using agent and exposes a function to call it."""

import logging

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import InMemorySaver

# Importing config here guarantees load_dotenv() has run before we build the
# model below (the model reads ANTHROPIC_API_KEY from the environment).
from langchain_poc import config
from langchain_poc.tools import add, get_current_time, multiply

# A named logger for this module. The name shows up in each log line, so you can
# tell agent logs apart from uvicorn's.
logger = logging.getLogger(__name__)

model = ChatAnthropic(model=config.MODEL_NAME, max_tokens=1024)

# The checkpointer is the agent's memory. After every step it saves the running
# message history, keyed by a "thread_id" we pass on each call. Next time we call
# with the same thread_id, the agent reloads that history and keeps the conversation
# going. InMemorySaver keeps it in a plain dict, so memory is lost when the server
# restarts — swap in SqliteSaver/PostgresSaver to persist across restarts.
checkpointer = InMemorySaver()


# Creates agent, tools it can use, and its system prtomp
# Agent will go through tools to get a response before returning the result
agent = create_agent(
    model,
    tools=[get_current_time, add, multiply],
    # Not a bad idea to re-emphasize tools in the system prompt so the agent doesn't ignore them
    system_prompt="""You are a helpful, friendly assistant. Keep your answers concise —
one or two sentences unless the user asks for more detail. When the user asks about the
current date or time, use the get_current_time tool instead of guessing.""",
    checkpointer=checkpointer,
)


async def stream_ask(message: str, thread_id: str = "default"):
    """Run the agent and yield the reply text token-by-token as it's produced.

        ReAct loop (Reason + Act)
            - Agent calls model -> runs tool -> calls model again
            - In more complex scenarios, orchestrates to other agents

        We ask for stream_mode updates and messages
            TLDR: messages are the tokenized response. updates are, well, updates (LLM call, Tool response, complete (non-tokenized) AI message)

        thread_id picks WHICH conversation this message belongs to. The checkpointer
        keeps a separate history per thread_id, so two callers with different ids
        get independent memories (and the same id continues an existing chat).

        See README for more
    """
    logger.info(f"USER asked (stream) [thread={thread_id}]: {message}")

    # The config tells the checkpointer which conversation to load/save.
    config = {"configurable": {"thread_id": thread_id}}

    parts = []  # Collect the streamed tokens so we can log the full reply at the end
    async for mode, payload in agent.astream(
        {"messages": [("user", message)]},
        config,
        stream_mode=["updates", "messages"],
    ):
        if mode == "messages":
            # Stream returned a chunk of a message. Return it to the user
            chunk, _metadata = payload
            text = _chunk_text(chunk)
            if text:
                parts.append(text)
                yield text
        elif mode == "updates":
            # Stream returned an AIMessage or ToolMessage. Log it so we have updates and continue.
            # See README for more on these)
            for node_update in payload.values():
                if isinstance(node_update, dict):
                    for m in node_update.get("messages", []):
                        _log_step(m)

    logger.info(f"FINAL reply: {''.join(parts)}")


def _chunk_text(chunk) -> str:
    """Pull the plain text out of a streamed message chunk.

    Anthropic sometimes hands back content as a simple string, and sometimes as a
    list of "content blocks" (dicts like {"type": "text", "text": "..."}). This
    normalizes both so callers always get a string (empty string for non-text
    chunks, e.g. the ones that carry tool-call arguments)."""
    content = chunk.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def _log_step(m) -> None:
    """Log a single message from the agent's run: a user turn, the model asking
    for a tool, a tool result, or the final answer. Shared by both endpoints so
    their logs look the same."""
    kind = m.__class__.__name__  # Reads class name - HumanMessage / AIMessage / ToolMessage / SystemMessage / ChatMessage / REmoveMessage / BaseMessage
    tool_calls = getattr(m, "tool_calls", None)
    if tool_calls:
        for call in tool_calls:
            logger.info(f"  {kind} -> calling tool {call['name']}({call['args']})")
    elif m.content:
        logger.info(f"  {kind}: {_chunk_text(m)}")