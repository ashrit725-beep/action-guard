"""Keep signed links out of the server's own request log.

Approval and invitation links carry a signed token in the address, and the token
is all it takes to open that link. The web server prints every address it serves
in its access log, so each line is filtered here before it is written.
"""
from __future__ import annotations

import logging
import re

_TOKEN_IN_PATH = re.compile(
    r"(/(?:approvals|invites|approve|join)/)[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]{4,})?"
)


def hide_tokens(text: str) -> str:
    return _TOKEN_IN_PATH.sub(r"\1[hidden]", text)


class HideTokens(logging.Filter):
    """uvicorn writes access lines with the arguments (client, method, path, http_version, status)."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            record.args = args[:2] + (hide_tokens(args[2]),) + args[3:]
        return True


def install() -> None:
    logging.getLogger("uvicorn.access").addFilter(HideTokens())
