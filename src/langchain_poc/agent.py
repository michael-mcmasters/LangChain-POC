"""The AI layer: builds a tool-using agent and exposes a function to call it."""

import logging
from datetime import datetime

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

# Importing config here guarantees load_dotenv() has run before we build the
# model below (the model reads ANTHROPIC_API_KEY from the environment).
from langchain_poc import config

# A named logger for this module. The name shows up in each log line, so you can
# tell agent logs apart from uvicorn's.
logger = logging.getLogger(__name__)

model = ChatAnthropic(model=config.MODEL_NAME, max_tokens=1024)


# A tool is just a Python function the model can choose to call. The @tool
# decorator turns it into something the agent understands. The docstring is
# NOT a comment — the model reads it to decide when this tool is useful.
@tool
def get_current_time() -> str:
    """Return the current date and time. Use this whenever the user asks what
    time or date it is, since you cannot know the current time on your own."""
    logger.info("This is a tool log message")
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# create_agent builds the loop: send the message + tool list to the model,
# run any tool the model asks for, feed the result back, repeat until it answers.
agent = create_agent(model, tools=[get_current_time])


def ask(message: str) -> str:
    """Run the agent on a message and return the final reply text."""
    logger.info(f"USER asked: {message}")

    result = agent.invoke({"messages": [("user", message)]})
    logger.info(result)

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
