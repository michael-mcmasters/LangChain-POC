"""Shared streaming helpers used by BOTH agent packages.

Both orchestrators (agent-as-tool and deepagents) are LangGraph agents, so the
code that runs them and turns their streamed output into typed events for the API
is identical. It lives here so each package's agent.py only has to differ in HOW
it builds the agent — not in how we stream it. That makes the two patterns easy
to compare side by side.
"""

import logging

from langchain_core.messages import AIMessage, ToolMessage

logger = logging.getLogger(__name__)


async def stream_agent(agent, message: str, thread_id: str):
    """Run a LangGraph agent and yield a stream of typed EVENTS as it works.

        ReAct loop (Reason + Act)
            - Agent calls model -> runs tool -> calls model again
            - In more complex scenarios, orchestrates to other agents

        We ask for stream_mode updates and messages
            TLDR: messages are the tokenized response. updates are, well, updates
            (LLM call, Tool response, complete (non-tokenized) AI message)

        Each conversation has a thread_id (passed from the client). The agent's
        checkpointer uses this to remember the conversation history.

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
            # A chunk of the model's answer. Forward the text as a token event.
            chunk, _metadata = payload
            text = chunk_text(chunk)
            if text:
                parts.append(text)
                yield {"type": "token", "content": text}

        # The agent returns updates (see README for more on these)
        elif mode == "updates":
            for node_update in payload.values():
                if isinstance(node_update, dict):
                    for m in node_update.get("messages", []):
                        for event in message_events(m):
                            yield event

    logger.info(f"FINAL reply: {''.join(parts)}")


def chunk_text(chunk) -> str:
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


def message_events(m):
    """
    Log an agent update and turn it into a typed event for the EventStream
    response. The client decides how/if to use these events.

    For example, the agent returns a ToolMessage as an update (the output of one
    of our tool functions). We log it and emit it as "tool_message" so the client
    is aware of it.

    (The agent-as-tool specialist wrappers reuse log_message directly — they log
    their own updates but do NOT emit client events.)
    """
    log_message(m)
    if isinstance(m, AIMessage) and m.tool_calls:
        for call in m.tool_calls:
            yield {"type": "tool_call", "name": call["name"], "args": call["args"]}
    elif isinstance(m, ToolMessage):
        yield {"type": "tool_message", "name": m.name, "content": chunk_text(m)}


def log_message(m) -> None:
    """Log a single agent update (a tool call, a tool result, etc.).

    Split out from message_events so both callers can reuse it: the orchestrator
    logs AND emits client events (above), while the agent-as-tool specialist
    wrappers only want the logging. Logging never touches the message state, so
    reusing it here has no effect on context isolation."""
    if isinstance(m, AIMessage) and m.tool_calls:
        for call in m.tool_calls:
            logger.info(f"  {type(m).__name__}: tool_call -> {call['name']}({call['args']})")
    elif isinstance(m, ToolMessage):
        logger.info(f"  {type(m).__name__}: tool_message -> {m.name}: {chunk_text(m)}")
    elif isinstance(m, AIMessage):
        # Final LLM response (no tool_calls) — nothing to log at the update level.
        pass
    else:
        logger.warning(f"  unhandled LLM update {type(m).__name__}: {m}")
