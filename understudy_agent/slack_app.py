import os
import re
import json
import ssl
import logging
from typing import Optional, Union, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import certifi

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from understudy_agent.schemas import LiveAction, Commitment, Clarification
from understudy_agent.ledger import (
    update_action_status,
    update_commitment_status,
    record_nudge,
    update_commitment_follow_up,
    get_commitment,
    get_action,
    find_action,
    answer_clarification,
    find_clarification,
)
from understudy_agent import google_delivery

logger = logging.getLogger("understudy.slack")

# Load environment variables from understudy_agent/.env and root
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

# Category emoji helper
CATEGORY_EMOJIS = {
    "email": "📧",
    "calendar": "📅",
    "doc": "📄",
    "research": "🔍",
    "task": "✅",
    "slack": "💬",
}

STATUS_EMOJIS = {
    "queued": "⏳ Queued",
    "running": "⚡ Running",
    "done": "✅ Done",
    "needs_approval": "⚠️ Needs Approval",
    "error": "❌ Error",
    "open": "📋 Open",
    "in_progress": "🔄 In Progress",
    "blocked": "🚫 Blocked",
    "overdue": "🚨 Overdue",
}

_shared_ssl_context: Optional[ssl.SSLContext] = None

def get_ssl_context() -> ssl.SSLContext:
    """Returns the shared singleton SSL context configured with certifi CA certificates."""
    global _shared_ssl_context
    if _shared_ssl_context is None:
        try:
            _shared_ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            _shared_ssl_context = ssl.create_default_context()
    return _shared_ssl_context

def get_slack_client() -> WebClient:
    """Returns a configured Slack WebClient with shared certifi SSL context."""
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    return WebClient(token=bot_token, ssl=get_ssl_context())

from slack_sdk.webhook import WebhookClient

def update_message_in_place(
    body: Dict[str, Any],
    respond: Any,
    client: Any,
    blocks: list,
    text: str,
) -> None:
    """Updates a Slack message in place via respond, WebhookClient, or chat_update using certifi SSL."""
    # Ensure respond carries the certifi SSL context
    if hasattr(respond, "ssl") and respond.ssl is None:
        respond.ssl = get_ssl_context()

    # 1. Try respond()
    try:
        if respond:
            respond(replace_original=True, blocks=blocks, text=text)
            return
    except Exception as e:
        logger.debug(f"Could not update message via respond: {e}")

    # 2. Try direct WebhookClient with shared certifi SSL context
    response_url = body.get("response_url")
    if response_url:
        try:
            webhook = WebhookClient(url=response_url, ssl=get_ssl_context())
            webhook.send(replace_original=True, blocks=blocks, text=text)
            return
        except Exception as e:
            logger.debug(f"Could not update message via WebhookClient: {e}")

    # 3. Fallback to client.chat_update with shared certifi SSL context
    try:
        chat_client = client if (client and getattr(client, "ssl", None) is not None) else get_slack_client()
        channel_id = body.get("channel", {}).get("id")
        message_ts = body.get("message", {}).get("ts")
        if channel_id and message_ts:
            chat_client.chat_update(
                channel=channel_id,
                ts=message_ts,
                blocks=blocks,
                text=text,
            )
    except Exception as e:
        logger.warning(f"Error updating message in place: {e}")

def create_app() -> App:
    """Initializes and returns the Slack Bolt App with all action handlers and certifi SSL."""
    client = get_slack_client()
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    
    app = App(client=client, signing_secret=signing_secret)

    @app.middleware
    def _inject_shared_ssl(req, resp, next):
        if hasattr(req, "context"):
            if getattr(req.context, "client", None) and getattr(req.context.client, "ssl", None) is None:
                req.context.client.ssl = get_ssl_context()
            if getattr(req.context, "respond", None) and getattr(req.context.respond, "ssl", None) is None:
                req.context.respond.ssl = get_ssl_context()
        return next()

    # ---------------------------------------------------------
    # Action Approval Handlers (approve / edit / skip)
    # ---------------------------------------------------------
    @app.action("action_approve")
    def handle_action_approve(ack, body, client, respond):
        # 1. Acknowledge the interaction immediately (< 3s)
        ack()
        
        user_id = body.get("user", {}).get("id", "user")
        user_name = body.get("user", {}).get("name", "someone")
        action_payload = body["actions"][0]["value"]
        
        try:
            parsed = json.loads(action_payload)
            meeting_id = parsed.get("meeting_id")
            action_id = parsed.get("action_id")
            title = parsed.get("title", "Action Item")
        except Exception:
            parts = action_payload.split(":", 1)
            meeting_id = parts[0] if len(parts) > 1 else "demo-meeting"
            action_id = parts[1] if len(parts) > 1 else parts[0]
            title = "Action Item"

        # If meeting_id is missing or placeholder, try to find the action
        if not meeting_id or meeting_id == "unknown":
            found_mid, _ = find_action(action_id)
            if found_mid:
                meeting_id = found_mid
            else:
                meeting_id = "demo-meeting"

        print(f"[Slack] Approving action {action_id} in meeting {meeting_id} by @{user_name}...")
        
        # Check if action has an associated Gmail draftId
        draft_id = None
        action_dict = None
        try:
            action_dict = get_action(meeting_id, action_id)
        except Exception:
            pass

        if action_dict:
            draft_id = action_dict.get("draftId")
            if not draft_id and action_dict.get("artifact"):
                m = re.search(r"Draft ID:\s*([a-zA-Z0-9_-]+)", action_dict["artifact"])
                if m:
                    draft_id = m.group(1)

        reasoning = f"Approved & executed via Slack by @{user_name}."
        message_id = None

        if google_delivery.is_google_workspace_enabled() and draft_id:
            try:
                send_res = google_delivery.send_gmail_draft(draft_id)
                message_id = send_res.get("messageId")
                reasoning = f"Approved & sent Gmail draft (Message ID: {message_id}) via Slack by @{user_name}."
                logger.info(f"Sent Gmail draft '{draft_id}' on Slack approval -> messageId: '{message_id}'")
            except Exception as send_err:
                logger.error(f"Failed to send Gmail draft '{draft_id}': {send_err}")
                reasoning = f"Approved by @{user_name}, but error sending Gmail draft: {send_err}"

        # 2. Update Firestore ledger
        try:
            update_action_status(
                meeting_id=meeting_id,
                action_id=action_id,
                status="done",
                reasoning=reasoning,
            )
            # Also update commitment if promoted
            commitment_id = f"com-{action_id}" if not action_id.startswith("com-") else action_id
            if get_commitment(commitment_id):
                update_commitment_status(commitment_id, "done")
        except Exception as e:
            print(f"[Slack] Error updating Firestore ledger on approve: {e}")

        # 3. Update the Slack message in place
        original_blocks = body.get("message", {}).get("blocks", [])
        updated_blocks = []
        for b in original_blocks:
            if b.get("type") == "actions":
                # Replace button row with confirmation context
                updated_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"✅ *Approved & Executed* by <@{user_id}>"
                        }
                    ]
                })
            else:
                updated_blocks.append(b)

        update_message_in_place(body, respond, client, updated_blocks, f"✅ Approved: {title}")

    @app.action("action_edit")
    def handle_action_edit(ack, body, client, respond):
        ack()
        user_id = body.get("user", {}).get("id", "user")
        action_payload = body["actions"][0]["value"]
        
        try:
            parsed = json.loads(action_payload)
            title = parsed.get("title", "Action Item")
        except Exception:
            title = "Action Item"

        print(f"[Slack] Edit clicked for action {action_payload} by user <@{user_id}>...")
        
        original_blocks = body.get("message", {}).get("blocks", [])
        updated_blocks = []
        for b in original_blocks:
            if b.get("type") == "actions":
                updated_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"✏️ *Edit requested* by <@{user_id}> (Opening in dashboard...)"
                        }
                    ]
                })
            else:
                updated_blocks.append(b)

        update_message_in_place(body, respond, client, updated_blocks, f"✏️ Editing: {title}")

    @app.action("action_skip")
    def handle_action_skip(ack, body, client, respond):
        ack()
        user_id = body.get("user", {}).get("id", "user")
        user_name = body.get("user", {}).get("name", "someone")
        action_payload = body["actions"][0]["value"]
        
        try:
            parsed = json.loads(action_payload)
            meeting_id = parsed.get("meeting_id")
            action_id = parsed.get("action_id")
            title = parsed.get("title", "Action Item")
        except Exception:
            parts = action_payload.split(":", 1)
            meeting_id = parts[0] if len(parts) > 1 else "demo-meeting"
            action_id = parts[1] if len(parts) > 1 else parts[0]
            title = "Action Item"

        if not meeting_id or meeting_id == "unknown":
            found_mid, _ = find_action(action_id)
            if found_mid:
                meeting_id = found_mid
            else:
                meeting_id = "demo-meeting"

        print(f"[Slack] Skipping action {action_id} by @{user_name}...")
        
        try:
            update_action_status(
                meeting_id=meeting_id,
                action_id=action_id,
                status="error",
                reasoning=f"Skipped via Slack by @{user_name}.",
            )
        except Exception as e:
            print(f"[Slack] Error updating Firestore ledger on skip: {e}")

        original_blocks = body.get("message", {}).get("blocks", [])
        updated_blocks = []
        for b in original_blocks:
            if b.get("type") == "actions":
                updated_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"⏭️ *Skipped* by <@{user_id}>"
                        }
                    ]
                })
            else:
                updated_blocks.append(b)

        update_message_in_place(body, respond, client, updated_blocks, f"⏭️ Skipped: {title}")

    # ---------------------------------------------------------
    # Commitment Nudge Handlers (done / snooze / blocked)
    # ---------------------------------------------------------
    @app.action("commitment_done")
    def handle_commitment_done(ack, body, client, respond):
        ack()
        user_id = body.get("user", {}).get("id", "user")
        user_name = body.get("user", {}).get("name", "someone")
        commitment_payload = body["actions"][0]["value"]
        
        try:
            parsed = json.loads(commitment_payload)
            commitment_id = parsed.get("commitment_id", commitment_payload)
            title = parsed.get("title", "Commitment")
        except Exception:
            commitment_id = commitment_payload
            title = "Commitment"

        print(f"[Slack] Marking commitment {commitment_id} as DONE by @{user_name}...")
        
        try:
            update_commitment_status(commitment_id, "done")
            record_nudge(commitment_id, note=f"Marked done via Slack by @{user_name}")
        except Exception as e:
            print(f"[Slack] Error updating Firestore ledger for commitment done: {e}")

        original_blocks = body.get("message", {}).get("blocks", [])
        updated_blocks = []
        for b in original_blocks:
            if b.get("type") == "actions":
                updated_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"✅ *Marked Done* by <@{user_id}>"
                        }
                    ]
                })
            else:
                updated_blocks.append(b)

        update_message_in_place(body, respond, client, updated_blocks, f"✅ Completed: {title}")

    @app.action("commitment_snooze")
    def handle_commitment_snooze(ack, body, client, respond):
        ack()
        user_id = body.get("user", {}).get("id", "user")
        user_name = body.get("user", {}).get("name", "someone")
        commitment_payload = body["actions"][0]["value"]
        
        try:
            parsed = json.loads(commitment_payload)
            commitment_id = parsed.get("commitment_id", commitment_payload)
            title = parsed.get("title", "Commitment")
        except Exception:
            commitment_id = commitment_payload
            title = "Commitment"

        print(f"[Slack] Snoozing commitment {commitment_id} by @{user_name}...")
        
        next_nudge_str = "Tomorrow 9:00 AM"
        try:
            record_nudge(
                commitment_id=commitment_id,
                note=f"Snoozed via Slack by @{user_name}",
                next_nudge=next_nudge_str,
            )
        except Exception as e:
            print(f"[Slack] Error updating Firestore ledger for snooze: {e}")

        original_blocks = body.get("message", {}).get("blocks", [])
        updated_blocks = []
        for b in original_blocks:
            if b.get("type") == "actions":
                updated_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"⏰ *Snoozed until {next_nudge_str}* by <@{user_id}>"
                        }
                    ]
                })
            else:
                updated_blocks.append(b)

        update_message_in_place(body, respond, client, updated_blocks, f"⏰ Snoozed: {title}")

    @app.action("commitment_blocked")
    def handle_commitment_blocked(ack, body, client, respond):
        ack()
        user_id = body.get("user", {}).get("id", "user")
        user_name = body.get("user", {}).get("name", "someone")
        commitment_payload = body["actions"][0]["value"]
        
        try:
            parsed = json.loads(commitment_payload)
            commitment_id = parsed.get("commitment_id", commitment_payload)
            title = parsed.get("title", "Commitment")
        except Exception:
            commitment_id = commitment_payload
            title = "Commitment"

        print(f"[Slack] Marking commitment {commitment_id} as BLOCKED by @{user_name}...")
        
        try:
            update_commitment_status(commitment_id, "blocked")
            record_nudge(
                commitment_id=commitment_id,
                note=f"Marked blocked via Slack by @{user_name}",
            )
            # Update actionType to unblock
            comm_doc = get_commitment(commitment_id)
            if comm_doc:
                fu = comm_doc.get("followUp", {}) or {}
                fu["actionType"] = "unblock"
                update_commitment_follow_up(commitment_id, fu, status="blocked")
        except Exception as e:
            print(f"[Slack] Error updating Firestore ledger for blocked: {e}")

        original_blocks = body.get("message", {}).get("blocks", [])
        updated_blocks = []
        for b in original_blocks:
            if b.get("type") == "actions":
                updated_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🚫 *Marked Blocked* by <@{user_id}>"
                        }
                    ]
                })
            else:
                updated_blocks.append(b)

        update_message_in_place(body, respond, client, updated_blocks, f"🚫 Marked Blocked: {title}")

    # ---------------------------------------------------------
    # Clarification Question Handlers (quick-reply / dismiss)
    # ---------------------------------------------------------
    @app.action("clarification_quick_reply")
    def handle_clarification_quick_reply(ack, body, client, respond):
        ack()
        user_id = body.get("user", {}).get("id", "user")
        user_name = body.get("user", {}).get("name", "someone")
        action_payload = body["actions"][0]["value"]
        
        try:
            parsed = json.loads(action_payload)
            meeting_id = parsed.get("meeting_id")
            clarification_id = parsed.get("clarification_id")
            answer = parsed.get("answer", "Alex")
        except Exception:
            meeting_id = "demo-meeting"
            clarification_id = action_payload
            answer = "Alex"

        if not meeting_id or meeting_id == "unknown":
            found_mid, _ = find_clarification(clarification_id)
            if found_mid:
                meeting_id = found_mid
            else:
                meeting_id = "demo-meeting"

        print(f"[Slack] Clarification {clarification_id} in {meeting_id} answered with '{answer}' by @{user_name}...")
        
        # 1. Update Firestore ledger via answer_clarification
        try:
            answer_clarification(
                meeting_id=meeting_id,
                clarification_id=clarification_id,
                answer=answer,
                status="answered",
            )
        except Exception as e:
            print(f"[Slack] Error recording clarification answer: {e}")

        # 2. Resume execution
        try:
            from understudy_agent import server
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(server.resume_clarification_execution(meeting_id, clarification_id, answer))
                else:
                    loop.run_until_complete(server.resume_clarification_execution(meeting_id, clarification_id, answer))
            except Exception:
                asyncio.run(server.resume_clarification_execution(meeting_id, clarification_id, answer))
        except Exception as resume_err:
            print(f"[Slack] Error resuming execution for {clarification_id}: {resume_err}")

        # 3. Update Slack message in place
        original_blocks = body.get("message", {}).get("blocks", [])
        updated_blocks = []
        for b in original_blocks:
            if b.get("type") == "actions":
                updated_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"✅ *Clarified & Assigned to {answer}* by <@{user_id}> (Execution resumed)"
                        }
                    ]
                })
            else:
                updated_blocks.append(b)

        update_message_in_place(body, respond, client, updated_blocks, f"✅ Clarified: Assigned to {answer}")

    @app.action("clarification_dismiss")
    def handle_clarification_dismiss(ack, body, client, respond):
        ack()
        user_id = body.get("user", {}).get("id", "user")
        user_name = body.get("user", {}).get("name", "someone")
        action_payload = body["actions"][0]["value"]
        
        try:
            parsed = json.loads(action_payload)
            meeting_id = parsed.get("meeting_id")
            clarification_id = parsed.get("clarification_id")
        except Exception:
            meeting_id = "demo-meeting"
            clarification_id = action_payload

        if not meeting_id or meeting_id == "unknown":
            found_mid, _ = find_clarification(clarification_id)
            if found_mid:
                meeting_id = found_mid
            else:
                meeting_id = "demo-meeting"

        print(f"[Slack] Clarification {clarification_id} in {meeting_id} dismissed by @{user_name}...")
        
        try:
            answer_clarification(
                meeting_id=meeting_id,
                clarification_id=clarification_id,
                answer="Dismissed",
                status="dismissed",
            )
        except Exception as e:
            print(f"[Slack] Error updating clarification on dismiss: {e}")

        original_blocks = body.get("message", {}).get("blocks", [])
        updated_blocks = []
        for b in original_blocks:
            if b.get("type") == "actions":
                updated_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"⏭️ *Clarification Dismissed* by <@{user_id}>"
                        }
                    ]
                })
            else:
                updated_blocks.append(b)

        update_message_in_place(body, respond, client, updated_blocks, "⏭️ Clarification Dismissed")

    return app


# Singleton App instance
_app_instance: Optional[App] = None

def get_app() -> App:
    """Returns the singleton Slack Bolt App."""
    global _app_instance
    if _app_instance is None:
        _app_instance = create_app()
    return _app_instance

def get_default_channel() -> str:
    """Returns default target Slack channel from env."""
    return os.getenv("SLACK_CHANNEL", "#under-study")

# ----------------------------------------------------------------------
# Message Posting Helpers (Block Kit)
# ----------------------------------------------------------------------

def post_action_feed(
    action: Union[LiveAction, Dict[str, Any]],
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """Posts a message summarizing a live action to SLACK_CHANNEL using Block Kit."""
    app = get_app()
    target_channel = channel or get_default_channel()
    
    data = action.model_dump() if isinstance(action, LiveAction) else dict(action)
    category = data.get("category", "task")
    cat_emoji = CATEGORY_EMOJIS.get(category, "📌")
    title = data.get("title", "Action Item")
    status = data.get("status", "queued")
    status_badge = STATUS_EMOJIS.get(status, status)
    assignee = data.get("assignee") or "Unassigned"
    reasoning = data.get("reasoning", "")
    artifact = data.get("artifact")
    action_id = data.get("id", "")

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{cat_emoji} *{title}*\n*Assignee:* {assignee} | *Status:* `{status_badge}`"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"💡 *Reasoning:* {reasoning}"
            }
        }
    ]

    if artifact:
        artifact_preview = artifact if len(artifact) < 800 else artifact[:797] + "..."
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Artifact preview:*\n```{artifact_preview}```"
            }
        })

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Action ID: `{action_id}` | Category: `{category}` | Understudy Live Feed"
            }
        ]
    })

    fallback_text = f"[{category.upper()}] {title} ({status})"
    res = app.client.chat_postMessage(
        channel=target_channel,
        text=fallback_text,
        blocks=blocks,
    )
    return res.data

def post_approval(
    action: Union[LiveAction, Dict[str, Any]],
    channel: Optional[str] = None,
    meeting_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Posts a needs-approval message with Approve / Edit / Skip buttons."""
    app = get_app()
    target_channel = channel or get_default_channel()
    
    data = action.model_dump() if isinstance(action, LiveAction) else dict(action)
    category = data.get("category", "task")
    cat_emoji = CATEGORY_EMOJIS.get(category, "📌")
    title = data.get("title", "Action Item")
    assignee = data.get("assignee") or "Unassigned"
    reasoning = data.get("reasoning", "")
    artifact = data.get("artifact")
    action_id = data.get("id", "")
    actual_meeting_id = meeting_id or "demo-meeting"

    action_value = json.dumps({
        "meeting_id": actual_meeting_id,
        "action_id": action_id,
        "title": title,
    })

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⚠️ Action Requires Approval",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{cat_emoji} *{title}*\n*Assignee:* {assignee} | *Category:* `{category}`"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"💡 *Reasoning:* {reasoning}"
            }
        }
    ]

    if artifact:
        artifact_preview = artifact if len(artifact) < 1000 else artifact[:997] + "..."
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Draft Content:*\n```{artifact_preview}```"
            }
        })

    blocks.append({
        "type": "actions",
        "block_id": f"approval_actions_{action_id}",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve", "emoji": True},
                "style": "primary",
                "action_id": "action_approve",
                "value": action_value,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Edit", "emoji": True},
                "action_id": "action_edit",
                "value": action_value,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Skip", "emoji": True},
                "style": "danger",
                "action_id": "action_skip",
                "value": action_value,
            }
        ]
    })

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Action ID: `{action_id}` | Meeting: `{actual_meeting_id}`"
            }
        ]
    })

    fallback_text = f"⚠️ Approval Required: {title}"
    res = app.client.chat_postMessage(
        channel=target_channel,
        text=fallback_text,
        blocks=blocks,
    )
    return res.data

def post_nudge(
    commitment: Union[Commitment, Dict[str, Any]],
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """Posts a nudge message with Done / Snooze / Blocked buttons."""
    app = get_app()
    target_channel = channel or get_default_channel()
    
    data = commitment.model_dump() if isinstance(commitment, Commitment) else dict(commitment)
    category = data.get("category", "task")
    cat_emoji = CATEGORY_EMOJIS.get(category, "📌")
    title = data.get("title", "Commitment")
    assignee = data.get("assignee") or "Unassigned"
    due = data.get("due") or "No due date"
    status = data.get("status", "open")
    source_meeting = data.get("sourceMeeting", "Meeting")
    source_date = data.get("sourceDate", "")
    commitment_id = data.get("id", "")
    
    follow_up = data.get("followUp") or {}
    if isinstance(follow_up, dict):
        nudge_count = follow_up.get("nudgeCount", 0)
        note = follow_up.get("note", "")
    else:
        nudge_count = getattr(follow_up, "nudgeCount", 0) or 0
        note = getattr(follow_up, "note", "") or ""

    nudge_payload = json.dumps({
        "commitment_id": commitment_id,
        "title": title,
    })

    meeting_str = f"{source_meeting} ({source_date})" if source_date else source_meeting
    nudge_badge = f"Chased {nudge_count}×" if nudge_count > 0 else "First nudge"
    if note and note not in nudge_badge:
        nudge_badge += f" · {note}"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔔 Nudge: {title[:140]}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{cat_emoji} *{title}*\n*Assignee:* @{assignee} | *Due:* `{due}` | *Status:* `{status.upper()}`\n*Source:* {meeting_str}\n*Follow-up:* {nudge_badge}"
            }
        },
        {
            "type": "actions",
            "block_id": f"nudge_actions_{commitment_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Done", "emoji": True},
                    "style": "primary",
                    "action_id": "commitment_done",
                    "value": nudge_payload,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Snooze", "emoji": True},
                    "action_id": "commitment_snooze",
                    "value": nudge_payload,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Blocked", "emoji": True},
                    "style": "danger",
                    "action_id": "commitment_blocked",
                    "value": nudge_payload,
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Commitment ID: `{commitment_id}` | Understudy Follow-Up Scanner"
                }
            ]
        }
    ]

    fallback_text = f"🔔 Nudge for @{assignee}: {title} (Due: {due})"
    res = app.client.chat_postMessage(
        channel=target_channel,
        text=fallback_text,
        blocks=blocks,
    )
    return res.data

def post_clarification(
    clarification: Union[Clarification, Dict[str, Any]],
    channel: Optional[str] = None,
    meeting_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Posts a clarification question message with quick-reply buttons."""
    app = get_app()
    target_channel = channel or get_default_channel()
    
    data = clarification.model_dump() if isinstance(clarification, Clarification) else dict(clarification)
    clar_id = data.get("id", "")
    actual_meeting_id = data.get("meetingId") or meeting_id or "demo-meeting"
    question = data.get("question", "Could you clarify this action item?")
    related_text = data.get("relatedText", "")
    
    reply_alex_val = json.dumps({"meeting_id": actual_meeting_id, "clarification_id": clar_id, "answer": "Alex"})
    reply_sam_val = json.dumps({"meeting_id": actual_meeting_id, "clarification_id": clar_id, "answer": "Sam"})
    dismiss_val = json.dumps({"meeting_id": actual_meeting_id, "clarification_id": clar_id, "action": "dismiss"})
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "❓ Clarification Needed",
                "emoji": True,
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{question}*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"💬 *Related Transcript:* \"_{related_text}_\""
            }
        },
        {
            "type": "actions",
            "block_id": f"clarification_actions_{clar_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Assign to Alex", "emoji": True},
                    "style": "primary",
                    "action_id": "clarification_quick_reply",
                    "value": reply_alex_val,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Assign to Sam", "emoji": True},
                    "action_id": "clarification_quick_reply",
                    "value": reply_sam_val,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Dismiss", "emoji": True},
                    "style": "danger",
                    "action_id": "clarification_dismiss",
                    "value": dismiss_val,
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Clarification ID: `{clar_id}` | Meeting: `{actual_meeting_id}` | Understudy Agent"
                }
            ]
        }
    ]
    
    fallback_text = f"❓ Clarification: {question}"
    res = app.client.chat_postMessage(
        channel=target_channel,
        text=fallback_text,
        blocks=blocks,
    )
    return res.data


def get_socket_mode_handler() -> SocketModeHandler:
    """Creates and returns the SocketModeHandler instance."""
    app = get_app()
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not app_token:
        raise ValueError("SLACK_APP_TOKEN is missing in environment variables.")
    return SocketModeHandler(app, app_token)

def start_socket_mode() -> None:
    """Starts Socket Mode listening."""
    handler = get_socket_mode_handler()
    print("⚡ Starting Understudy Slack Bolt Socket Mode Handler...")
    handler.start()

if __name__ == "__main__":
    start_socket_mode()
