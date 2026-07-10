"""Pattern 1 — agents-as-tools: builds a tool-using orchestrator and exposes a function to call it."""

import logging
from pathlib import Path

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

# Importing config here guarantees load_dotenv() has run before we build the
# model below (the model reads ANTHROPIC_API_KEY from the environment).
from langchain_poc import config
from langchain_poc.streaming import chunk_text, log_message, stream_agent
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

# This pattern has no skills machinery, so we read the ascii-art skill off disk and
# inline it into the prompt ourselves (deepagents loads it lazily via SkillsMiddleware).
_ascii_skill = Path(__file__).resolve().parents[3] / "skills" / "ascii-art"
_ascii_art = (
    (_ascii_skill / "SKILL.md").read_text(encoding="utf-8")
    + "\n\n"
    + (_ascii_skill / "references" / "digits.txt").read_text(encoding="utf-8")
)

math_agent = create_agent(
    model,
    tools=[add, multiply],
    system_prompt="""You are a math specialist. Use the add and multiply tools to
compute exact answers — don't do the arithmetic in your head. Show the steps briefly.
When you present your FINAL numeric answer, follow the ascii-art skill below to render
that number as an ASCII-art banner.

"""
    + _ascii_art,
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
    """Stream this pattern's orchestrator as typed events (see streaming.stream_agent)."""
    async for event in stream_agent(agent, message, thread_id):
        yield event


async def _run_specialist(specialist, question: str) -> str:
    """Run a specialist agent to completion, logging each internal update as it
    happens, and return ONLY its final answer.

    We stream the specialist's `updates` purely so we can log them (via
    log_message). Those logs go to stdout — they never cross back to the
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
                    log_message(m)
                    # The terminal AIMessage (no tool calls) is the final answer.
                    if isinstance(m, AIMessage) and not m.tool_calls:
                        answer = chunk_text(m)
    return answer
