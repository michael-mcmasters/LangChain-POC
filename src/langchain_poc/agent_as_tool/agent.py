"""Pattern 1 — agents-as-tools: builds a tool-using orchestrator and exposes a function to call it."""

import logging

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


# --- Define SubAgents ---
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


# --- Define agents as tools so orchestrator agent can call them ---
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


# --- Define orchestrator agent, pass above specialist tools so orchetrator agent can call them
agent = create_agent(
    model,
    tools=[math_specialist, time_specialist],
    system_prompt="""You are an orchestrator. You do not do math or tell the time
yourself. Delegate math questions to the math_specialist tool and date/time questions
to the time_specialist tool. For anything else, answer directly and concisely.""",
    checkpointer=checkpointer,
)

# --- Inits agent loop ---
async def stream_ask(message: str, thread_id: str):
    """Stream this pattern's orchestrator as typed events (see streaming.stream_agent)."""
    # stream_agent is a shared method called by this package and deepagents package
    # This package defines the agents and then calls stream_agent to initaite the agent loop
    # The only difference between the two is how agents are defined.
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
