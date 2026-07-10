"""Pattern 2 — deepagents: the SAME delegation behavior as the agent-as-tool
package, but built with `create_deep_agent` instead of wiring specialists by hand.

Compare this file to agent_as_tool/agent.py. There we:
  - built each specialist as a full agent, AND
  - hand-wrote an @tool wrapper per specialist so the orchestrator could call it.

Here we just describe each specialist as a plain dict ("subagent") and hand the
list to create_deep_agent. The deep agent gives the orchestrator a built-in
`task` tool that delegates to a subagent by name — so we get the same isolated-
context delegation for free, plus batteries-included tools (write_todos, a
virtual filesystem: read_file / write_file) the orchestrator can use to plan.

Everything downstream is identical: create_deep_agent returns a LangGraph agent,
so streaming.stream_agent drives it exactly like the other pattern.
"""

import logging

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import InMemorySaver

# Resolves to the top-level `deepagents` LIBRARY, not this package (see __init__).
from deepagents import create_deep_agent

# Importing config here guarantees load_dotenv() has run before we build the model.
from langchain_poc import config
from langchain_poc.streaming import stream_agent
from langchain_poc.tools import add, get_current_time, multiply

logger = logging.getLogger(__name__)

model = ChatAnthropic(model=config.MODEL_NAME, max_tokens=1024)

# Same as Pattern 1: memory lives on the top-level orchestrator, keyed by thread_id.
checkpointer = InMemorySaver()


# --- Subagents: specialists described as plain dicts -----------------------
# This is the deepagents equivalent of Pattern 1's "specialist agent + @tool
# wrapper" pair. `description` is what the orchestrator reads to decide when to
# delegate (it played the role of the @tool docstring before). `system_prompt`
# and `tools` define the specialist itself. Its internal steps stay isolated —
# only its final summary returns to the orchestrator.

math_subagent = {
    "name": "math-agent",
    "description": "Delegate arithmetic — addition, multiplication, multi-step math — here.",
    "system_prompt": """You are a math specialist. Use the add and multiply tools to
compute exact answers — don't do the arithmetic in your head. Show the steps briefly.""",
    "tools": [add, multiply],
}

time_subagent = {
    "name": "time-agent",
    "description": "Delegate any question about the current date or time here.",
    "system_prompt": """You are a timekeeping specialist. Use get_current_time to answer
anything about the current date or time.""",
    "tools": [get_current_time],
}


# --- Orchestrator: a deep agent that delegates via its built-in `task` tool -
# We give it NO domain tools of its own (tools=[]) — just the subagents. The deep
# agent automatically adds a `task` tool it uses to hand work to a subagent by
# name, mirroring Pattern 1's math_specialist / time_specialist wrappers.

agent = create_deep_agent(
    model=model,
    tools=[],
    system_prompt="""You are an orchestrator. You do not do math or tell the time
yourself. Delegate math questions to the math-agent subagent and date/time questions
to the time-agent subagent. For anything else, answer directly and concisely.

For any request with more than one step, FIRST call the write_todos tool to record
your plan as a todo list, then update it (marking items completed) as you finish each
step. write_todos is a built-in deepagents tool — this is the "batteries included"
planning that the agent-as-tool pattern does not have.""",
    subagents=[math_subagent, time_subagent],
    checkpointer=checkpointer,
)


async def stream_ask(message: str, thread_id: str):
    """Public entry point: stream this pattern's orchestrator as typed events.

    Identical to the agent-as-tool package's stream_ask — same helper, different
    agent — which is the whole point: only the agent construction above differs."""
    async for event in stream_agent(agent, message, thread_id):
        yield event
