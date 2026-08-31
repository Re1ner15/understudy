from google.adk.agents import Agent
from understudy_agent.config import MODEL_ID

def echo(text: str) -> dict:
    """Returns the input text.

    Args:
        text: The text to echo.
    """
    return {"echo": text}

root_agent = Agent(
    name="understudy_agent",
    model=MODEL_ID,
    description="Echoes back whatever the user says, for scaffold testing.",
    instruction="You are a helpful agent. Whenever the user says something, use the echo tool to echo it back to them.",
    tools=[echo]
)
