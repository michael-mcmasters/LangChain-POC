"""The AI layer: builds a tool-using agent and exposes a function to call it."""

import logging

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

# Importing config here guarantees load_dotenv() has run before we build the
# model below (the model reads ANTHROPIC_API_KEY from the environment).
from langchain_poc import config
from langchain_poc.tools import add, get_current_time, multiply

# A named logger for this module. The name shows up in each log line, so you can
# tell agent logs apart from uvicorn's.
logger = logging.getLogger(__name__)

model = ChatAnthropic(model=config.MODEL_NAME, max_tokens=1024)

# Saves conversation history and steps by thread_id (passed by the client) in the server. Restarting the server loses history. Can store in a database to persist longer.
checkpointer = InMemorySaver()


# --- Specialist agents ----------------------------------------------------
# Each specialist is a FULL agent (its own ReAct loop) with a narrow job: its
# own system prompt and its own subset of tools. This is the heart of Pattern 1
# — instead of one agent holding every tool, we split the work across focused
# agents. Note there's no checkpointer here, so a specialist starts fresh on
# every call. Conversation memory lives on the orchestrator below, not here.

math_agent = create_agent(
    model,
    tools=[add, multiply],
    system_prompt="""You are a math specialist. Use the add and multiply tools to
compute exact answers — don't do the arithmetic in your head. Show the steps briefly.""",
)

time_agent = create_agent(
    model,
    tools=[get_current_time],
    system_prompt="""You are a timekeeping specialist. Use get_current_time to answer
anything about the current date or time.""",
)


# --- Wrapper tools: let the orchestrator delegate to a specialist ----------
# We wrap each specialist in an @tool. To the orchestrator these look like any
# other tool (just as add/multiply did) — but calling one runs a whole agent.
# The docstring is what the orchestrator reads to decide when to delegate.
# Only the specialist's FINAL text comes back; its internal steps stay isolated.
# These are async (ainvoke) so a specialist run doesn't block the event loop.

@tool
async def math_specialist(question: str) -> str:
    """Delegate arithmetic — addition, multiplication, multi-step math — to the
    math specialist. Pass the full math question as `question`."""
    logger.info(f"  routing to math_specialist: {question}")
    return await _run_specialist(math_agent, question)


@tool
async def time_specialist(question: str) -> str:
    """Delegate any question about the current date or time to the timekeeping
    specialist. Pass the user's question as `question`."""
    logger.info(f"  routing to time_specialist: {question}")
    return await _run_specialist(time_agent, question)


# --- Orchestrator: the top-level agent stream_ask() drives -----------------
# Holds NO domain tools of its own — only the two specialists. Its whole job is
# to route each request to the right one (or answer directly for small talk).
# This is the only agent with a checkpointer, so conversation memory lives here.

agent = create_agent(
    model,
    tools=[math_specialist, time_specialist],
    system_prompt="""You are an orchestrator. You do not do math or tell the time
yourself. Delegate math questions to the math_specialist tool and date/time questions
to the time_specialist tool. For anything else, answer directly and concisely.""",
    checkpointer=checkpointer,
)


async def stream_ask(message: str, thread_id: str):
    """Run the agent and yield a stream of typed EVENTS as it works.

        ReAct loop (Reason + Act)
            - Agent calls model -> runs tool -> calls model again
            - In more complex scenarios, orchestrates to other agents

        We ask for stream_mode updates and messages
            TLDR: messages are the tokenized response. updates are, well, updates (LLM call, Tool response, complete (non-tokenized) AI message)

        Each conversation has a thread_id (passed from the client). Checkpointer uses this to remember the conversation history.

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
            text = _chunk_text(chunk)
            if text:
                parts.append(text)
                yield {"type": "token", "content": text}
        
        # The agent returns updates (see README for more on these)
        elif mode == "updates":
            for node_update in payload.values():
                if isinstance(node_update, dict):
                    for m in node_update.get("messages", []):
                        for event in _message_events(m):
                            yield event

    logger.info(f"FINAL reply: {''.join(parts)}")


async def _run_specialist(specialist, question: str) -> str:
    """Run a specialist agent to completion, logging each internal update as it
    happens, and return ONLY its final answer.

    We stream the specialist's `updates` purely so we can log them (via
    _log_message). Those logs go to stdout — they never cross back to the
    orchestrator, which only ever sees this function's return value. So we get
    full server-side visibility while the context stays isolated:
    observe everything, return little."""
    answer = ""
    async for _mode, payload in specialist.astream(
        {"messages": [("user", question)]},
        stream_mode=["updates"],
    ):
        for node_update in payload.values():
            if isinstance(node_update, dict):
                for m in node_update.get("messages", []):
                    _log_message(m)
                    # The terminal AIMessage (no tool calls) is the final answer.
                    if isinstance(m, AIMessage) and not m.tool_calls:
                        answer = _chunk_text(m)
    return answer


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


def _message_events(m):
    """
    Log an agent update and, for the orchestrator, turn it into a typed event for
    the EventStream response. The client decides how/if to use these events.

    For example, the agent returns a ToolMessage as an update (the output of one
    of our tool functions). We log it and emit it as "tool_message" so the client
    is aware of it.

    (The specialist wrappers reuse _log_message directly — they log their own
    updates but do NOT emit client events.)
    """
    _log_message(m)
    if isinstance(m, AIMessage) and m.tool_calls:
        for call in m.tool_calls:
            yield {"type": "tool_call", "name": call["name"], "args": call["args"]}
    elif isinstance(m, ToolMessage):
        yield {"type": "tool_message", "name": m.name, "content": _chunk_text(m)}


def _log_message(m) -> None:
    """Log a single agent update (a tool call, a tool result, etc.).

    Split out from _message_events so both callers can reuse it: the orchestrator
    logs AND emits client events (above), while the specialist wrappers only want
    the logging. Logging never touches the message state, so reusing it here has
    no effect on context isolation."""
    if isinstance(m, AIMessage) and m.tool_calls:
        for call in m.tool_calls:
            logger.info(f"  {type(m).__name__}: tool_call -> {call['name']}({call['args']})")
    elif isinstance(m, ToolMessage):
        logger.info(f"  {type(m).__name__}: tool_message -> {m.name}: {_chunk_text(m)}")
    elif isinstance(m, AIMessage):
        # Final LLM response (no tool_calls) — nothing to log at the update level.
        pass
    else:
        logger.warning(f"  unhandled LLM update {type(m).__name__}: {m}")