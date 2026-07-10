"""Pattern 2 — deepagents: same delegation behavior as agent-as-tool, built with create_deep_agent."""

import logging
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import InMemorySaver

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from langchain_poc import config
from langchain_poc.streaming import stream_agent
from langchain_poc.tools import add, get_current_time, multiply

logger = logging.getLogger(__name__)

model = ChatAnthropic(model=config.MODEL_NAME, max_tokens=1024)
checkpointer = InMemorySaver()

# Scope the backend to the skills/ folder (read-only) so the agent's filesystem
# tools can read the skills but nothing else in the repo, and can't write at all.
SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"
backend = FilesystemBackend(root_dir=SKILLS_DIR, virtual_mode=True)
READ_ONLY = [FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")]

math_subagent = {
    "name": "math-agent",
    "description": "Delegate arithmetic — addition, multiplication, multi-step math — here.",
    "system_prompt": """You are a math specialist. Use the add and multiply tools to
compute exact answers — don't do the arithmetic in your head. Show the steps briefly.
When you present your FINAL numeric answer, follow the ascii-art skill to render that
number as an ASCII-art banner.""",
    "tools": [add, multiply],
    "skills": ["/"],
}

time_subagent = {
    "name": "time-agent",
    "description": "Delegate any question about the current date or time here.",
    "system_prompt": """You are a timekeeping specialist. Use get_current_time to answer
anything about the current date or time.""",
    "tools": [get_current_time],
}

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
    backend=backend,
    permissions=READ_ONLY,
    checkpointer=checkpointer,
)


async def stream_ask(message: str, thread_id: str):
    async for event in stream_agent(agent, message, thread_id):
        yield event
