# SPDX-License-Identifier: MPL-2.0
"""Logging setup with redaction of secrets.

Logs go to stderr (journald when run by systemd). Request/response bodies,
headers and customer names are never logged; as a second line of defence every
registered secret is replaced by ``***`` in all log output.
"""

from __future__ import annotations

import logging
import sys

_SECRETS: set[str] = set()


def register_secret(value: str | None) -> None:
    if value and len(value) >= 4:
        _SECRETS.add(value)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not _SECRETS:
            return True
        message = record.getMessage()
        redacted = message
        for secret in _SECRETS:
            redacted = redacted.replace(secret, "***")
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True


def setup_logging(debug: bool = False) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    # httpx/httpcore log URLs and headers on DEBUG; keep them quiet in every mode.
    for name in ("httpx", "httpcore", "dbus_fast"):
        logging.getLogger(name).setLevel(logging.WARNING)
