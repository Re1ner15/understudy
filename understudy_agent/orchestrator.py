import asyncio
from datetime import datetime
from understudy_agent.schemas import ActionItemBatch, ToolResult, ActionItem
from understudy_agent.tools.handlers import (
    draft_email,
    create_calendar,
    create_doc,
    research,
    create_task,
    draft_slack,
)

async def orchestrate(batch: ActionItemBatch) -> list[ToolResult]:
    semaphore = asyncio.Semaphore(3)
    
    async def process_item(item: ActionItem) -> ToolResult:
        async with semaphore:
            start_time = datetime.now().strftime("%H:%M:%S")
            print(f"[{start_time}] Starting item {item.id} ({item.category})...")
            
            try:
                if item.category == "email":
                    result = await draft_email(item)
                elif item.category == "calendar":
                    result = await create_calendar(item)
                elif item.category == "doc":
                    result = await create_doc(item)
                elif item.category == "research":
                    result = await research(item)
                elif item.category == "task":
                    result = await create_task(item)
                elif item.category == "slack":
                    result = await draft_slack(item)
                else:
                    raise ValueError(f"Unknown category: {item.category}")
            except Exception as e:
                result = ToolResult(
                    item_id=item.id,
                    category=item.category,
                    status="error",
                    summary=f"Error: {e}",
                    artifact=None,
                    requires_approval=False,
                )
                
            finish_time = datetime.now().strftime("%H:%M:%S")
            print(f"[{finish_time}] Finished item {item.id} ({item.category}).")
            return result

    tasks = [process_item(item) for item in batch.items]
    return await asyncio.gather(*tasks)
