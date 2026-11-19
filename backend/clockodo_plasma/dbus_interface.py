# SPDX-License-Identifier: MPL-2.0
"""Session D-Bus interface for the Plasma widget.

All arguments and return values are strings; structured data is JSON. This
keeps the marshalling between Python and the QML D-Bus module trivial and
avoids int64 precision issues in JavaScript.

Deliberately small (docs/en/architecture.md, "D-Bus interface"): no method returns the
API key or raw API responses, there is no generic HTTP pass-through, and start
only accepts ids that the daemon itself loaded from Clockodo.
"""

# No "from __future__ import annotations": dbus-fast reads the signature
# strings from the annotations at runtime.

import json
import logging
from typing import Any

from dbus_fast.service import ServiceInterface, method, signal

from . import DBUS_INTERFACE
from .service import Service
from .state import State

log = logging.getLogger(__name__)


def _loads(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text) if text else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


class ClockodoInterface(ServiceInterface):
    def __init__(self, service: Service) -> None:
        super().__init__(DBUS_INTERFACE)
        self.service = service
        self._last_state = ""
        service.add_listener(self._on_state)

    def _on_state(self, state: State) -> None:
        text = state.to_json()
        if text != self._last_state:
            self._last_state = text
            self.StateChanged(text)

    @signal()
    def StateChanged(self, state: "s") -> "s":  # noqa: F821, UP037
        return state

    @method()
    def GetState(self) -> "s":  # noqa: F821, UP037
        return self.service.state.to_json()

    @method()
    def Refresh(self) -> None:
        self.service.request_sync()

    @method()
    async def ListContexts(self) -> "s":  # noqa: F821, UP037
        return _dumps(await self.service.list_contexts())

    @method()
    async def Start(self, context: "s") -> "s":  # noqa: F821, UP037
        return _dumps(await self.service.start(_loads(context)))

    @method()
    async def Stop(self, entry_id: "s") -> "s":  # noqa: F821, UP037
        try:
            entry = int(entry_id)
        except ValueError:
            return _dumps({"ok": False, "message": "invalid entry id"})
        return _dumps(await self.service.stop(entry))

    @method()
    async def Switch(self, context: "s", entry_id: "s") -> "s":  # noqa: F821, UP037
        try:
            entry = int(entry_id)
        except ValueError:
            return _dumps({"ok": False, "message": "invalid entry id"})
        return _dumps(await self.service.switch(_loads(context), entry))

    @method()
    async def SetCredentials(self, email: "s", api_key: "s") -> "s":  # noqa: F821, UP037
        return _dumps(await self.service.set_credentials(email, api_key))

    @method()
    async def Unlock(self) -> "s":  # noqa: F821, UP037
        return _dumps(await self.service.unlock())

    @method()
    def GetSettings(self) -> "s":  # noqa: F821, UP037
        return _dumps(self.service.get_settings())

    @method()
    async def SetSettings(self, settings: "s") -> "s":  # noqa: F821, UP037
        return _dumps(await self.service.set_settings(_loads(settings)))
