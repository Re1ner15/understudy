from google.adk.agents import LlmAgent
from understudy_agent.config import MODEL_ID
from .schemas import ActionItemBatch

watcher = LlmAgent(
    name="watcher",
    model=MODEL_ID,
    description="Extracts structured action items from a meeting transcript.",
    instruction=(
        "You are an assistant that extracts ONLY concrete, actionable commitments and decisions "
        "from a meeting transcript. Each commitment becomes one ActionItem. "
        "Categorize each action item as 'email', 'calendar', 'doc', 'research', 'task', 'slack', or 'code'. "
        "Use category 'slack' when the action is to notify or ping a team or person via a chat or Slack message. "
        "Use category 'code' when the action involves the codebase, repository, app, or website itself — "
        "e.g. fixing a bug, changing app/website copy or content, updating a page, adding a feature, or opening a pull request. "
        "Capture the assignee if a person is named, and a due date if mentioned. "
        "IMPORTANT: capture DELEGATED commitments too — when a speaker assigns work to "
        "someone else (e.g. 'Matthew will review the research', 'Priya will order the "
        "laptops', 'can you research X'), extract it as an action item with that person "
        "as the assignee. Do this even when the phrasing is soft ('once it's ready', "
        "'this week') — a named owner plus a task is a commitment. "
        "Ignore greetings, opinions, and non-actionable discussion. "
        "Do not invent tasks that were never mentioned, but do NOT drop clearly stated "
        "commitments just because they are phrased casually. "
        "Assign a stable short id like 'ai-1', 'ai-2', etc. for each."
    ),
    output_schema=ActionItemBatch,
)
