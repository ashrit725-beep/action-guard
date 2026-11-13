"""Outbound email for Vexen.

Nothing on a request path ever talks to an SMTP server. A caller writes a row
into `email_outbox`; one background worker drains it. That keeps authorization
decisions fast, survives a slow or rate-limiting mail provider, and means a
broken mailbox can never take the product down — the mail simply waits.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("vexen.mail")

MAX_ATTEMPTS = 5
BATCH_SIZE = 12
WORKER_INTERVAL_SECONDS = 5
SEND_TIMEOUT_SECONDS = 30

# Personal Gmail mailboxes allow roughly 500 recipients per rolling 24 hours.
# We keep well under that and slow down rather than getting the mailbox blocked.
SEND_SPACING_SECONDS = 0.6


class MailError(Exception):
    """Sending failed. `terminal` means retrying will not help."""

    def __init__(self, message: str, *, terminal: bool = False) -> None:
        super().__init__(message)
        self.terminal = terminal


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def smtp_settings() -> Dict[str, Any]:
    port_raw = (os.environ.get("SMTP_PORT") or "587").strip()
    try:
        port = int(port_raw)
    except ValueError:
        port = 587
    username = (os.environ.get("SMTP_USERNAME") or "").strip()
    return {
        "host": (os.environ.get("SMTP_HOST") or "").strip(),
        "port": port,
        "username": username,
        # Gmail app passwords are shown in four groups of four; the spaces are
        # cosmetic and must be stripped before authenticating.
        "password": (os.environ.get("SMTP_PASSWORD") or "").replace(" ", "").strip(),
        "from_email": (os.environ.get("SMTP_FROM_EMAIL") or username).strip(),
        "from_name": (os.environ.get("SMTP_FROM_NAME") or "Vexen Security").strip(),
    }


def smtp_configured() -> bool:
    settings = smtp_settings()
    return all([settings["host"], settings["username"], settings["password"], settings["from_email"]])


def public_app_url(base_url: Optional[str] = None) -> str:
    """The address a person on their phone can actually open."""
    from .urls import configured_public_url

    # A configured address always wins: request headers are chosen by the caller.
    return configured_public_url() or (base_url or "").strip().rstrip("/")


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------
def _build_message(*, to: str, subject: str, text: str, html: str,
                   settings: Dict[str, Any]) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings["from_name"], settings["from_email"]))
    message["To"] = to
    message["Reply-To"] = settings["from_email"]
    message["Message-ID"] = make_msgid(domain="vexen.app")
    message["Auto-Submitted"] = "auto-generated"
    message["X-Vexen-Mailer"] = "vexen-outbox"
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


async def send_now(*, to: str, subject: str, text: str, html: str) -> None:
    """Send one message over SMTP. Raises MailError on failure."""
    settings = smtp_settings()
    if not smtp_configured():
        raise MailError("SMTP is not configured", terminal=False)

    try:
        import aiosmtplib
    except ImportError as exc:  # pragma: no cover - dependency is installed
        raise MailError(f"aiosmtplib missing: {exc}", terminal=True) from exc

    message = _build_message(to=to, subject=subject, text=text, html=html, settings=settings)
    use_implicit_tls = settings["port"] == 465
    try:
        await aiosmtplib.send(
            message,
            hostname=settings["host"],
            port=settings["port"],
            username=settings["username"],
            password=settings["password"],
            start_tls=not use_implicit_tls,
            use_tls=use_implicit_tls,
            timeout=SEND_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 - normalise every provider failure
        name = type(exc).__name__
        detail = str(exc)[:300]
        # A rejected app password will never start working on its own.
        terminal = "Authentication" in name or "535" in detail or "534" in detail
        raise MailError(f"{name}: {detail}", terminal=terminal) from exc


# ---------------------------------------------------------------------------
# Outbox
# ---------------------------------------------------------------------------
async def queue_email(db, *, to: str, subject: str, text: str, html: str, kind: str,
                      org_id: Optional[str] = None, user_id: Optional[str] = None,
                      dedupe_key: Optional[str] = None) -> Optional[str]:
    """Add one message to the outbox. Never raises — email is never critical path."""
    address = (to or "").strip()
    if not address or "@" not in address:
        return None
    doc = {
        "id": "eml_" + uuid.uuid4().hex[:20],
        "org_id": org_id,
        "user_id": user_id,
        "to": address,
        "subject": subject[:200],
        "text": text,
        "html": html,
        "kind": kind,
        "status": "queued",
        "attempts": 0,
        "last_error": None,
        "dedupe_key": dedupe_key,
        "created_at": _now(),
        "next_attempt_at": _now(),
        "sent_at": None,
    }
    try:
        await db.email_outbox.insert_one(doc)
        return doc["id"]
    except Exception as exc:  # noqa: BLE001 - duplicate dedupe key or db hiccup
        logger.info("Email not queued (%s): %s", kind, str(exc)[:160])
        return None


async def _claim_next(db) -> Optional[Dict[str, Any]]:
    """Atomically take one due message so two workers can never send it twice."""
    return await db.email_outbox.find_one_and_update(
        {"status": "queued", "next_attempt_at": {"$lte": _now()}},
        {"$set": {"status": "sending", "claimed_at": _now()}},
        sort=[("created_at", 1)],
        return_document=True,
    )


STUCK_AFTER_SECONDS = 300  # longer than SEND_TIMEOUT_SECONDS, so a send still in progress is never taken back


async def recover_stuck(db) -> int:
    """Put messages back in the queue when a worker stopped in the middle of sending.

    A deploy or restart can stop the worker after it claimed a message and before
    it recorded the result. Without this the message would stay "sending" forever.
    """
    result = await db.email_outbox.update_many(
        {"status": "sending", "claimed_at": {"$lt": _now() - timedelta(seconds=STUCK_AFTER_SECONDS)}},
        {"$set": {"status": "queued", "next_attempt_at": _now()}},
    )
    if result.modified_count:
        logger.warning("Returned %s unsent email(s) to the queue after an interrupted send.",
                       result.modified_count)
    return int(result.modified_count)


async def _record_failure(db, row: Dict[str, Any], error: str, *, terminal: bool) -> None:
    attempts = int(row.get("attempts") or 0) + 1
    give_up = terminal or attempts >= MAX_ATTEMPTS
    backoff = min(30 * (2 ** attempts), 1800)
    await db.email_outbox.update_one(
        {"id": row["id"]},
        {"$set": {
            "status": "failed" if give_up else "queued",
            "attempts": attempts,
            "last_error": error[:300],
            "next_attempt_at": _now() + timedelta(seconds=backoff),
            "failed_at": _now() if give_up else None,
        }},
    )


async def drain_once(db, *, limit: int = BATCH_SIZE) -> Dict[str, int]:
    """Send up to `limit` queued messages. Returns a small counters dict."""
    sent = failed = 0
    for _ in range(limit):
        row = await _claim_next(db)
        if not row:
            break
        try:
            await send_now(to=row["to"], subject=row["subject"],
                           text=row.get("text") or "", html=row.get("html") or "")
        except MailError as exc:
            failed += 1
            await _record_failure(db, row, str(exc), terminal=exc.terminal)
            if exc.terminal:
                logger.error("Email permanently failed for %s: %s", row["kind"], str(exc)[:160])
            # A provider that just refused us is unlikely to accept the next one
            # immediately, so stop this pass and let the worker retry later.
            break
        except Exception as exc:  # noqa: BLE001 - never let the worker die
            failed += 1
            await _record_failure(db, row, f"unexpected: {exc}", terminal=False)
            break
        else:
            sent += 1
            await db.email_outbox.update_one(
                {"id": row["id"]},
                {"$set": {"status": "sent", "sent_at": _now(), "last_error": None},
                 "$inc": {"attempts": 1}},
            )
            await asyncio.sleep(SEND_SPACING_SECONDS)
    return {"sent": sent, "failed": failed}


async def outbox_worker(stop_event: asyncio.Event) -> None:
    """Background loop started with the app. Quiet, resilient, easy to stop."""
    from .db import get_db

    if not smtp_configured():
        logger.warning("Email is not configured — alerts will queue until SMTP details are added.")
    while not stop_event.is_set():
        try:
            if smtp_configured():
                db = get_db()
                await recover_stuck(db)
                await drain_once(db)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as exc:  # noqa: BLE001 - the worker must never die
            logger.error("Outbox worker error: %s", str(exc)[:200])
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=WORKER_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


async def outbox_stats(db, *, org_id: Optional[str] = None) -> Dict[str, Any]:
    scope: Dict[str, Any] = {"org_id": org_id} if org_id else {}
    counts = {}
    for state in ("queued", "sending", "sent", "failed"):
        counts[state] = await db.email_outbox.count_documents({**scope, "status": state})
    latest = await (db.email_outbox.find(scope, {"_id": 0, "html": 0, "text": 0})
                    .sort("created_at", -1).limit(10).to_list(10))
    return {"configured": smtp_configured(), "counts": counts, "recent": latest}


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
BRAND = "#048ea9"
INK = "#0f172a"
MUTED = "#5a6b80"
BORDER = "#e2e8f0"
CANVAS = "#f6f9fb"
ALLOW = "#0f8a7b"
BLOCK = "#c8202f"
AMBER = "#b8760a"


def _esc(value: Any) -> str:
    text = "" if value is None else str(value)
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;"))


def _money(amount: Optional[float], currency: str = "USD") -> Optional[str]:
    if amount is None:
        return None
    symbol = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}.get((currency or "USD").upper(), "")
    try:
        return f"{symbol}{float(amount):,.2f}"
    except (TypeError, ValueError):
        return None


def _shell(*, heading: str, intro: str, rows: List[Tuple[str, str]], buttons: str,
           footer: str, accent: str = BRAND) -> str:
    row_html = "".join(
        f"""<tr>
            <td style="padding:7px 0;font:500 12px/1.4 Helvetica,Arial,sans-serif;color:{MUTED};
                       text-transform:uppercase;letter-spacing:.06em;white-space:nowrap;
                       vertical-align:top;width:38%">{_esc(label)}</td>
            <td style="padding:7px 0;font:400 14px/1.5 Helvetica,Arial,sans-serif;color:{INK};
                       vertical-align:top">{value}</td>
          </tr>"""
        for label, value in rows
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{_esc(heading)}</title></head>
<body style="margin:0;padding:0;background:{CANVAS};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:{CANVAS};padding:24px 12px;">
  <tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="max-width:560px;background:#ffffff;border:1px solid {BORDER};border-radius:14px;">
      <tr><td style="padding:20px 24px 0 24px;">
        <span style="font:700 16px/1 Helvetica,Arial,sans-serif;color:{INK};letter-spacing:-.02em;">
          Vex<span style="color:{BRAND}">e</span>n</span>
        <span style="font:600 10px/1 Helvetica,Arial,sans-serif;color:{MUTED};
                     letter-spacing:.18em;margin-left:8px;">CONTROL AI</span>
      </td></tr>
      <tr><td style="padding:14px 24px 0 24px;">
        <div style="height:3px;width:44px;background:{accent};border-radius:2px;"></div>
        <h1 style="margin:14px 0 0 0;font:600 21px/1.3 Helvetica,Arial,sans-serif;color:{INK};">
          {_esc(heading)}</h1>
        <p style="margin:10px 0 0 0;font:400 15px/1.6 Helvetica,Arial,sans-serif;color:{MUTED};">
          {intro}</p>
      </td></tr>
      <tr><td style="padding:18px 24px 0 24px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="border-top:1px solid {BORDER};border-bottom:1px solid {BORDER};">
          {row_html}
        </table>
      </td></tr>
      <tr><td style="padding:20px 24px 4px 24px;">{buttons}</td></tr>
      <tr><td style="padding:8px 24px 24px 24px;">
        <p style="margin:0;font:400 12px/1.6 Helvetica,Arial,sans-serif;color:{MUTED};">{footer}</p>
      </td></tr>
    </table>
    <p style="max-width:560px;margin:14px auto 0 auto;font:400 11px/1.6 Helvetica,Arial,sans-serif;
              color:{MUTED};text-align:center;">
      Vexen decides, every single time, whether what your agents are about to do is allowed.
      You can turn these emails off in Settings &rsaquo; Alerts.
    </p>
  </td></tr>
</table>
</body></html>"""


def _button(label: str, href: str, colour: str, *, outline: bool = False) -> str:
    if outline:
        return (f'<a href="{_esc(href)}" style="display:inline-block;padding:13px 22px;'
                f'border-radius:10px;border:1px solid {colour};color:{colour};background:#ffffff;'
                f'font:600 15px/1 Helvetica,Arial,sans-serif;text-decoration:none;'
                f'min-width:132px;text-align:center;">{_esc(label)}</a>')
    return (f'<a href="{_esc(href)}" style="display:inline-block;padding:13px 22px;'
            f'border-radius:10px;background:{colour};color:#ffffff;'
            f'font:600 15px/1 Helvetica,Arial,sans-serif;text-decoration:none;'
            f'min-width:132px;text-align:center;">{_esc(label)}</a>')


def approval_alert_email(*, approval: Dict[str, Any], agent_name: str, workspace: str,
                         permission_label: str, decide_url: str, console_url: str,
                         recipient_name: str = "") -> Tuple[str, str, str]:
    """Subject, plain text and HTML for "an agent is waiting for you"."""
    amount = _money(approval.get("amount"), approval.get("currency") or "USD")
    what = permission_label or approval.get("permission_key") or "an action"
    subject = f"Vexen: {agent_name} needs your OK" + (f" for {amount}" if amount else "")

    rows: List[Tuple[str, str]] = [
        ("Agent", f'<strong style="color:{INK}">{_esc(agent_name)}</strong>'),
        ("Wants to", _esc(what)),
    ]
    if amount:
        rows.append(("Amount", f'<strong style="color:{INK}">{_esc(amount)}</strong>'))
    if approval.get("resource_id"):
        rows.append(("On", f'<span style="font-family:monospace;font-size:13px">'
                           f'{_esc(approval["resource_id"])}</span>'))
    rows.append(("Why it paused", _esc(approval.get("reason") or "A rule asked for a human.")))
    rows.append(("Workspace", _esc(workspace)))

    approve_url = f"{decide_url}?intent=approve"
    refuse_url = f"{decide_url}?intent=refuse"
    buttons = (
        f'<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
        f'<td style="padding:0 10px 10px 0">{_button("Approve once", approve_url, ALLOW)}</td>'
        f'<td style="padding:0 0 10px 0">{_button("Refuse", refuse_url, BLOCK, outline=True)}</td>'
        f"</tr></table>"
    )
    footer = (
        "Nothing has happened yet — the agent is stopped until you decide. "
        "You will be shown the details again before anything is confirmed. "
        "An approval is good for one attempt within 30 minutes. "
        f'<a href="{_esc(console_url)}" style="color:{BRAND}">Open Vexen instead</a>.'
    )
    html = _shell(heading="An agent is waiting for you",
                  intro=(f"{_esc(recipient_name.split(' ')[0]) + ', ' if recipient_name else ''}"
                         f"<strong style=\"color:{INK}\">{_esc(agent_name)}</strong> tried to do "
                         f"something that needs a person to say yes."),
                  rows=rows, buttons=buttons, footer=footer, accent=AMBER)

    text_lines = [
        f"{agent_name} is waiting for your OK.",
        "",
        f"Wants to: {what}",
    ]
    if amount:
        text_lines.append(f"Amount: {amount}")
    if approval.get("resource_id"):
        text_lines.append(f"On: {approval['resource_id']}")
    text_lines += [
        f"Why it paused: {approval.get('reason') or 'A rule asked for a human.'}",
        f"Workspace: {workspace}",
        "",
        f"Approve: {approve_url}",
        f"Refuse:  {refuse_url}",
        "",
        "Nothing has happened yet. The agent is stopped until you decide.",
        "An approval is good for one attempt within 30 minutes.",
        f"Open Vexen: {console_url}",
    ]
    return subject, "\n".join(text_lines), html


def invite_email(*, workspace: str, role_label: str, inviter: str, join_url: str,
                 role_summary: str) -> Tuple[str, str, str]:
    subject = f"{inviter} invited you to {workspace} on Vexen"
    rows = [
        ("Workspace", f'<strong style="color:{INK}">{_esc(workspace)}</strong>'),
        ("Your role", f'<strong style="color:{INK}">{_esc(role_label)}</strong>'),
        ("That means", _esc(role_summary)),
        ("Invited by", _esc(inviter)),
    ]
    buttons = _button("Accept the invitation", join_url, BRAND)
    footer = ("This invitation expires in 7 days. If you were not expecting it, "
              "you can safely ignore this email.")
    html = _shell(heading="You have been invited to Vexen",
                  intro=(f"<strong style=\"color:{INK}\">{_esc(inviter)}</strong> wants you to help "
                         f"keep an eye on the AI agents in {_esc(workspace)}."),
                  rows=rows, buttons=buttons, footer=footer)
    text = "\n".join([
        f"{inviter} invited you to the {workspace} workspace on Vexen.",
        "",
        f"Your role: {role_label} — {role_summary}",
        "",
        f"Accept: {join_url}",
        "",
        "This invitation expires in 7 days.",
    ])
    return subject, text, html


def team_joined_email(*, workspace: str, joiner_name: str, joiner_email: str,
                      role_label: str, team_url: str) -> Tuple[str, str, str]:
    subject = f"Vexen: {joiner_name} joined {workspace}"
    rows = [
        ("Who", f'<strong style="color:{INK}">{_esc(joiner_name)}</strong>'),
        ("Email", _esc(joiner_email)),
        ("Role", _esc(role_label)),
        ("Workspace", _esc(workspace)),
    ]
    buttons = _button("See your team", team_url, BRAND)
    html = _shell(heading=f"{_esc(joiner_name)} joined your workspace",
                  intro=(f"They accepted their invitation and can now sign in as "
                         f"<strong style=\"color:{INK}\">{_esc(role_label)}</strong>."),
                  rows=rows, buttons=buttons,
                  footer="You can turn these off in Settings &rsaquo; Alerts.",
                  accent=ALLOW)
    text = "\n".join([
        f"{joiner_name} ({joiner_email}) joined {workspace} as {role_label}.",
        "",
        f"See your team: {team_url}",
    ])
    return subject, text, html


def test_email(*, workspace: str, console_url: str) -> Tuple[str, str, str]:
    subject = "Vexen email is working"
    rows = [
        ("Workspace", f'<strong style="color:{INK}">{_esc(workspace)}</strong>'),
        ("What this proves", "Vexen can reach your inbox, so approval alerts will arrive."),
    ]
    buttons = _button("Open Vexen", console_url, BRAND)
    html = _shell(heading="Email is working",
                  intro="This is the test message you asked for. Nothing else to do.",
                  rows=rows, buttons=buttons,
                  footer="You can change which emails you receive in Settings &rsaquo; Alerts.",
                  accent=ALLOW)
    text = ("Vexen email is working.\n\n"
            f"Workspace: {workspace}\n"
            f"Open Vexen: {console_url}\n")
    return subject, text, html


def contact_message_email(*, reference: str, name: str, email: str, company: Optional[str],
                          topic: str, message: str) -> Tuple[str, str, str]:
    """The site owner's copy of a message sent from the website's contact page."""

    def one_line(value: str, limit: int) -> str:
        return " ".join((value or "").split())[:limit]  # a subject can never carry a line break

    subject = f"New message on Vexen ({one_line(topic, 40)}) from {one_line(name, 60)}"
    rows = [
        ("From", f'<strong style="color:{INK}">{_esc(name)}</strong> &lt;{_esc(email)}&gt;'),
        ("Company", _esc(company) or "-"),
        ("Topic", _esc(topic)),
        ("Message", _esc(message).replace("\n", "<br>")),
        ("Reference", _esc(reference)),
    ]
    html = _shell(heading="New contact message",
                  intro="Someone wrote to you from the website's contact page. Reply to the address above.",
                  rows=rows, buttons="",
                  footer="The message is also saved in the contact_messages collection.",
                  accent=BRAND)
    text = ("New message from the website's contact page.\n\n"
            f"From: {name} <{email}>\n"
            f"Company: {company or '-'}\n"
            f"Topic: {topic}\n"
            f"Reference: {reference}\n\n"
            f"{message}\n")
    return subject, text, html
