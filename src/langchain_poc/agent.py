"""The AI layer: builds a tool-using agent and exposes a function to call it."""

import logging

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic

# Importing config here guarantees load_dotenv() has run before we build the
# model below (the model reads ANTHROPIC_API_KEY from the environment).
from langchain_poc import config
from langchain_poc.tools import add, get_current_time, multiply

# A named logger for this module. The name shows up in each log line, so you can
# tell agent logs apart from uvicorn's.
logger = logging.getLogger(__name__)

model = ChatAnthropic(model=config.MODEL_NAME, max_tokens=1024)


# Creates agent, tools it can use, and its system prtomp
# Agent will go through tools to get a response before returning the result
agent = create_agent(
    model,
    tools=[get_current_time, add, multiply],
    # Not a bad idea to re-emphasize tools in the system prompt so the agent doesn't ignore them
    system_prompt="""You are a helpful, friendly assistant. Keep your answers concise —
one or two sentences unless the user asks for more detail. When the user asks about the
current date or time, use the get_current_time tool instead of guessing.""",
)


def ask(message: str) -> str:
    """Run the agent on a message and return the final reply text."""
    logger.info(f"USER asked: {message}")

    result = agent.invoke({"messages": [("user", message)]})
    logger.info(f"Raw Dump: {result}")

    # Walk the whole conversation the agent produced and log each step so you can
    # see the loop: user turn -> model asks for a tool -> tool result -> answer.
    for m in result["messages"]:
        kind = m.__class__.__name__  # HumanMessage / AIMessage / ToolMessage
        tool_calls = getattr(m, "tool_calls", None)
        if tool_calls:
            for call in tool_calls:
                logger.info(f"  {kind} -> calling tool {call['name']}({call['args']})")
        elif m.content:
            logger.info(f"  {kind}: {m.content}")

    reply = result["messages"][-1].content
    logger.info(f"FINAL reply: {reply}")
    return reply
