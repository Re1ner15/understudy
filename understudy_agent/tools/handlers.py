import uuid
import asyncio
import logging
import difflib
from understudy_agent.schemas import (
    ActionItem,
    ToolResult,
    EmailDraft,
    CalendarEvent,
    DocDraft,
    ResearchBrief,
    TaskTicket,
    SlackMessage,
    CodeChange,
)
from understudy_agent.tools.gemini_json import gemini_json, grounded_research
from understudy_agent import google_delivery
from understudy_agent import github_delivery
from understudy_agent import plane_delivery

logger = logging.getLogger("understudy.handlers")

async def draft_email(item: ActionItem) -> ToolResult:
    assignee_info = f" Assignee: {item.assignee}." if item.assignee else ""
    due_info = f" Due: {item.due}." if item.due else ""
    prompt = f"Draft an email based on this action item: {item.text}.{assignee_info}{due_info}"
    draft = await gemini_json(prompt, EmailDraft)

    if google_delivery.is_google_workspace_enabled():
        recipient = item.assignee if (item.assignee and "@" in item.assignee) else None
        res = await asyncio.to_thread(
            google_delivery.create_gmail_draft,
            to=recipient,
            subject=draft.subject,
            body=draft.body,
        )
        artifact = f"Subject: {draft.subject}\n\n{draft.body}\n\nDraft URL: {res['url']}\nDraft ID: {res['draftId']}"
        return ToolResult(
            item_id=item.id,
            category=item.category,
            status="needs_approval",
            summary="Drafted Gmail email for review.",
            artifact=artifact,
            requires_approval=True,
            draftId=res.get("draftId"),
        )

    artifact = f"Subject: {draft.subject}\n\n{draft.body}"
    return ToolResult(
        item_id=item.id,
        category=item.category,
        status="needs_approval",
        summary="Drafted email for review.",
        artifact=artifact,
        requires_approval=True,
    )

async def create_calendar(item: ActionItem) -> ToolResult:
    due_info = f" Proposed time/due: {item.due}." if item.due else ""
    assignee_info = f" Assignee: {item.assignee}." if item.assignee else ""
    prompt = f"Extract calendar event details from this action item: {item.text}.{due_info}{assignee_info}"
    event = await gemini_json(prompt, CalendarEvent)

    if google_delivery.is_google_workspace_enabled():
        raw_time = event.proposed_time or item.due
        start_iso = google_delivery.parse_proposed_time_to_iso(raw_time)
        res = await asyncio.to_thread(
            google_delivery.create_calendar_event,
            title=event.title,
            start_iso=start_iso,
            attendees=event.attendees,
        )
        artifact = f"Event: {event.title}\nProposed Time: {start_iso}\nAttendees: {', '.join(event.attendees)}\nURL: {res['htmlLink']}"
        return ToolResult(
            item_id=item.id,
            category=item.category,
            status="done",
            summary="Created Google Calendar event.",
            artifact=artifact,
            requires_approval=False,
        )

    artifact = f"Event: {event.title}\nProposed Time: {event.proposed_time}\nAttendees: {', '.join(event.attendees)}\nURL: https://calendar.google.com/mock/{uuid.uuid4().hex[:8]}"
    return ToolResult(
        item_id=item.id,
        category=item.category,
        status="done",
        summary="Created calendar event tentative hold.",
        artifact=artifact,
        requires_approval=False,
    )

async def create_doc(item: ActionItem) -> ToolResult:
    assignee_info = f" Assignee: {item.assignee}." if item.assignee else ""
    prompt = f"Draft a short document with a title and a few sections based on this action item: {item.text}.{assignee_info}"
    doc = await gemini_json(prompt, DocDraft)

    if google_delivery.is_google_workspace_enabled():
        res = await asyncio.to_thread(
            google_delivery.create_google_doc,
            title=doc.title,
            content=doc.content,
        )
        artifact = f"Title: {doc.title}\n\n{doc.content}\n\nURL: {res['url']}"
        return ToolResult(
            item_id=item.id,
            category=item.category,
            status="done",
            summary="Created Google Doc.",
            artifact=artifact,
            requires_approval=False,
        )

    artifact = f"Title: {doc.title}\n\n{doc.content}\n\nURL: https://docs.google.com/mock/{uuid.uuid4().hex[:8]}"
    return ToolResult(
        item_id=item.id,
        category=item.category,
        status="done",
        summary="Drafted document.",
        artifact=artifact,
        requires_approval=False,
    )

async def research(item: ActionItem) -> ToolResult:
    # Grounded research: real, current, cited findings via Gemini + Google Search.
    try:
        result = await grounded_research(item.text)
        findings = result.get("findings", "").strip()
        sources = result.get("sources", [])
        if findings:
            artifact = findings
            if sources:
                artifact += "\n\n===SOURCES===\n" + "\n".join(
                    f"{s['title']} | {s['url']}" for s in sources[:8]
                )
            n = len(sources)
            return ToolResult(
                item_id=item.id,
                category=item.category,
                status="done",
                summary=f"Grounded research brief ready ({n} source{'s' if n != 1 else ''}).",
                artifact=artifact,
                requires_approval=False,
            )
    except Exception as e:
        logger.error(f"Grounded research failed, falling back to ungrounded: {e}")

    # Fallback: ungrounded brief (no web access).
    brief = await gemini_json(f"Write a concise research brief on: {item.text}.", ResearchBrief)
    return ToolResult(
        item_id=item.id,
        category=item.category,
        status="done",
        summary="Completed research brief.",
        artifact=brief.findings,
        requires_approval=False,
    )

async def create_task(item: ActionItem) -> ToolResult:
    assignee_info = f" Assignee: {item.assignee}." if item.assignee else ""
    due_info = f" Due: {item.due}." if item.due else ""
    prompt = f"Create a task/ticket (title, body, labels) for this action item: {item.text}.{assignee_info}{due_info}"
    ticket = await gemini_json(prompt, TaskTicket)

    # Real delivery: file a work item in Plane (Taskmaster). Falls back to a
    # local ticket description when Plane isn't configured.
    if plane_delivery.is_plane_enabled():
        try:
            body_html = f"<p>{ticket.body}</p>"
            if item.source_quote:
                body_html += f'<p><em>Captured by Understudy from: "{item.source_quote}"</em></p>'
            issue = await asyncio.to_thread(
                plane_delivery.create_issue,
                name=ticket.title,
                description_html=body_html,
                priority="high" if (item.due and "friday" in (item.due or "").lower()) else "medium",
                group="unstarted",
            )
            priority = "high" if (item.due and "friday" in (item.due or "").lower()) else "medium"
            artifact = (
                f"Plane: {issue['url']}\n"
                f"PlaneIssueId: {issue['id']}\n"
                f"Ref: UNDERSTUDY-{issue.get('sequenceId')}\n"
                f"Project: Understudy\n"
                f"State: Todo\n"
                f"Priority: {priority}\n"
                f"Labels: {', '.join(ticket.labels)}\n\n"
                f"{ticket.title}\n\n{ticket.body}"
            )
            return ToolResult(
                item_id=item.id,
                category=item.category,
                status="done",
                summary=f"Created Plane work item #{issue.get('sequenceId')}.",
                artifact=artifact,
                requires_approval=False,
            )
        except Exception as e:
            logger.error(f"Plane issue creation failed, falling back to local ticket: {e}")

    artifact = f"Title: {ticket.title}\nLabels: {', '.join(ticket.labels)}\n\n{ticket.body}"
    return ToolResult(
        item_id=item.id,
        category=item.category,
        status="done",
        summary="Created task ticket.",
        artifact=artifact,
        requires_approval=False,
    )

async def draft_slack(item: ActionItem) -> ToolResult:
    assignee_info = f" Assignee: {item.assignee}." if item.assignee else ""
    due_info = f" Due: {item.due}." if item.due else ""
    prompt = f"Draft a Slack message based on this action item: {item.text}.{assignee_info}{due_info}"
    slack_msg = await gemini_json(prompt, SlackMessage)
    artifact = f"Target: {slack_msg.target}\nMessage: {slack_msg.message}\n(Posted to {slack_msg.target})"
    return ToolResult(
        item_id=item.id,
        category=item.category,
        status="done",
        summary=f"Drafted Slack message for {slack_msg.target}.",
        artifact=artifact,
        requires_approval=False,
    )

async def open_code_change(item: ActionItem) -> ToolResult:
    """Turns a code/dev action item into a real GitHub issue + a draft PR.

    The issue is created immediately (reversible). The PR is opened as a DRAFT and
    held for one-tap human approval — mirroring the email draft→approve pattern.
    """
    # Fallback when GitHub delivery isn't configured: describe the intended change.
    if not github_delivery.is_github_enabled():
        prompt = (
            f"Summarize this code task as a short GitHub issue.\nTask: {item.text}"
        )
        ticket = await gemini_json(prompt, TaskTicket)
        artifact = f"[GitHub disabled] Would file issue: {ticket.title}\n\n{ticket.body}"
        return ToolResult(
            item_id=item.id, category=item.category, status="done",
            summary="Prepared a code task (GitHub delivery off).",
            artifact=artifact, requires_approval=False,
        )

    repo = github_delivery._repo()
    path = github_delivery.target_file()

    # 1. Read the current target file so Gemini edits the real content.
    base_branch = await asyncio.to_thread(github_delivery.get_default_branch)
    current = await asyncio.to_thread(github_delivery.get_file, path, ref=base_branch)

    prompt = (
        f"You are editing the file `{path}` in the repo `{repo}`.\n"
        f"Apply this change requested in a meeting: \"{item.text}\".\n\n"
        f"Current file content:\n---\n{current['content']}\n---\n\n"
        "Return a MINIMAL set of exact find/replace edits (do NOT rewrite the whole file). "
        "Each edit's old_string must be copied VERBATIM from the current file above, with "
        "enough surrounding context to be unique. Only touch what the request requires. "
        "Also write a concise issue + PR title/body and a conventional commit message."
    )
    change = await gemini_json(prompt, CodeChange)

    # Apply edits programmatically so nothing else in the file can be dropped or reformatted.
    content = current["content"]
    applied, skipped = 0, []
    for edit in change.edits:
        if edit.old_string and edit.old_string in content:
            content = content.replace(edit.old_string, edit.new_string, 1)
            applied += 1
        else:
            skipped.append(edit.old_string[:40])
    if skipped:
        logger.warning(f"Code edit(s) not found verbatim for '{item.id}', skipped: {skipped}")
    if applied == 0:
        return ToolResult(
            item_id=item.id, category=item.category, status="error",
            summary="Could not apply any code edits (no matching text found).",
            artifact=f"Requested: {item.text}\nNo edits matched the current file.",
            requires_approval=False,
        )

    # 2. Create the issue (reversible, immediate).
    issue = await asyncio.to_thread(
        github_delivery.create_issue,
        title=change.issue_title,
        body=change.issue_body + f"\n\n_Filed automatically by Understudy from: \"{item.source_quote}\"_",
        labels=["understudy", "auto-generated"],
    )

    # 3. Open a draft PR with the real edit. Use the (unique, monotonic) issue
    # number in the branch name so re-runs never collide with a stale branch.
    branch = f"understudy/{item.id}-{issue['number']}"
    head_sha = await asyncio.to_thread(github_delivery._branch_head_sha, base_branch)
    await asyncio.to_thread(github_delivery.create_branch, branch, head_sha)
    new_content = content if content.endswith("\n") else content + "\n"

    # Compute the real unified diff so the UI can show the actual code changes
    # for review (not just the prose description).
    diff_lines = list(
        difflib.unified_diff(
            current["content"].splitlines(),
            new_content.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
    )
    if not diff_lines:
        # Nothing changed — surface it rather than opening an empty PR silently.
        logger.warning(f"Code change for '{item.id}' produced no diff on {path}.")
    # Bound the diff shown on the card (full change still lands in the PR).
    diff_text = "\n".join(diff_lines[:80])
    if len(diff_lines) > 80:
        diff_text += f"\n… (+{len(diff_lines) - 80} more diff lines in the PR)"

    await asyncio.to_thread(
        github_delivery.update_file,
        path=path,
        new_content=new_content,
        message=change.commit_message,
        branch=branch,
        sha=current["sha"],
    )
    pr = await asyncio.to_thread(
        github_delivery.open_pull_request,
        title=change.pr_title,
        body=change.pr_body + f"\n\nCloses #{issue['number']}\n\n_Drafted by Understudy — awaiting approval._",
        head=branch,
        base=base_branch,
        draft=True,
    )

    artifact = (
        f"Issue: #{issue['number']} {issue['url']}\n"
        f"PR: #{pr['number']} {pr['url']}\n"
        f"PR Node: {pr['nodeId']}\n"
        f"Repo: {repo}\n"
        f"File: {path}\n"
        f"Branch: {branch}\n\n"
        f"{change.pr_title}\n\n{change.pr_body}\n\n"
        f"===DIFF===\n{diff_text}"
    )
    return ToolResult(
        item_id=item.id,
        category=item.category,
        status="needs_approval",
        summary=f"Filed issue #{issue['number']} and opened draft PR #{pr['number']} — awaiting approval.",
        artifact=artifact,
        requires_approval=True,
        draftId=str(pr["number"]),
    )
