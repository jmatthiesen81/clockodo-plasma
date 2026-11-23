# SPDX-License-Identifier: MPL-2.0
"""Credential storage in the freedesktop Secret Service.

On Plasma 6 the Secret Service is provided by KWallet (``ksecretd``). The
daemon never unlocks the collection on its own; ``unlock()`` is only called
when the user presses "Unlock" in the widget.

``secretstorage`` is synchronous; all functions are run in a worker thread.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass

import secretstorage
from secretstorage.exceptions import (
    ItemNotFoundException,
    LockedException,
    PromptDismissedException,
    SecretServiceNotAvailableException,
)

from . import APP_ID

log = logging.getLogger(__name__)

ATTRIBUTES = {"application": APP_ID}
LABEL = "Clockodo API key (clockodo-plasma)"


class SecretUnavailable(Exception):
    """No Secret Service provider on the session bus."""


class SecretLocked(Exception):
    """The collection is locked or access was denied."""


@dataclass(frozen=True)
class Credentials:
    email: str
    api_key: str

    def __repr__(self) -> str:  # never show the key in logs or tracebacks
        return f"Credentials(email={self.email!r}, api_key=***)"


def _connect():
    try:
        return secretstorage.dbus_init()
    except SecretServiceNotAvailableException as exc:
        raise SecretUnavailable(str(exc)) from None


def _collection(conn):
    try:
        return secretstorage.get_default_collection(conn)
    except SecretServiceNotAvailableException as exc:
        raise SecretUnavailable(str(exc)) from None
    except (ItemNotFoundException, LockedException) as exc:
        raise SecretLocked(str(exc)) from None


def _load_sync() -> Credentials | None:
    conn = _connect()
    try:
        collection = _collection(conn)
        if collection.is_locked():
            raise SecretLocked("collection is locked")
        try:
            for item in collection.search_items(ATTRIBUTES):
                if item.is_locked():
                    raise SecretLocked("item is locked")
                email = item.get_attributes().get("account", "")
                key = item.get_secret().decode("utf-8")
                if email and key:
                    return Credentials(email, key)
        except LockedException as exc:
            raise SecretLocked(str(exc)) from None
        return None
    finally:
        with contextlib.suppress(Exception):
            conn.close()


def _store_sync(credentials: Credentials) -> None:
    conn = _connect()
    try:
        collection = _collection(conn)
        if collection.is_locked():
            raise SecretLocked("collection is locked")
        try:
            # Store the new item first and only then remove older ones (e.g. a
            # different account): if storing fails, the old credentials stay.
            created = collection.create_item(
                LABEL,
                {**ATTRIBUTES, "account": credentials.email},
                credentials.api_key.encode("utf-8"),
                replace=True,
            )
            for item in list(collection.search_items(ATTRIBUTES)):
                if item != created:
                    item.delete()
        except LockedException as exc:
            raise SecretLocked(str(exc)) from None
    finally:
        with contextlib.suppress(Exception):
            conn.close()


def _unlock_sync() -> bool:
    conn = _connect()
    try:
        collection = _collection(conn)
        if not collection.is_locked():
            return True
        try:
            dismissed = collection.unlock()
        except PromptDismissedException:
            return False
        return not dismissed and not collection.is_locked()
    finally:
        with contextlib.suppress(Exception):
            conn.close()


class SecretStore:
    async def load(self) -> Credentials | None:
        return await asyncio.to_thread(_load_sync)

    async def store(self, credentials: Credentials) -> None:
        await asyncio.to_thread(_store_sync, credentials)

    async def unlock(self) -> bool:
        return await asyncio.to_thread(_unlock_sync)
