# SPDX-License-Identifier: MPL-2.0
"""Settings (``~/.config/clockodo-plasma/config.toml``) and small persistent data
(``~/.local/state/clockodo-plasma/state.json``).

Credentials are never stored here; they live in the Secret Service.
"""

from __future__ import annotations

import json
import logging
import os
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import APP_ID
from .api import Context
from .messages import LANGUAGES, SYSTEM

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1
POLL_INTERVALS = (0, 30, 60, 120, 300)
MAX_RECENT_CONTEXTS = 5
PANEL_STYLES = ("ring", "stopwatch", "pill")
MODIFIERS = ("ctrl", "shift", "alt", "meta")
CLICK_ACTIONS = ("quick", "picker", "none")  # quick start/stop, open the picker, nothing


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_ID


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / APP_ID


@dataclass
class Settings:
    schema_version: int = SCHEMA_VERSION
    poll_interval: int = 60  # seconds, 0 = off
    contact_email: str = ""  # empty = the Clockodo e-mail of the user
    notify_on_lock: bool = True
    long_running_hours: int = 0  # 0 = off
    language: str = SYSTEM  # "system" or a code from messages.LANGUAGES

    # Default booking for the quick start; 0 = not set.
    default_customers_id: int = 0
    default_projects_id: int = 0
    default_services_id: int = 0
    default_text: str = ""

    # Panel and mouse.
    panel_style: str = "ring"
    colorize: bool = True  # running green, stopped orange, over target red
    modifier: str = "ctrl"
    modifier_click: str = "quick"  # action of modifier + left click
    middle_click: str = "quick"

    # Daily target.
    overtime_color: bool = True
    overtime_notify: bool = True
    overtime_after_minutes: int = 0  # tolerance before the first warning
    overtime_repeat_minutes: int = 60  # 0 = warn once per day

    def validate(self) -> None:
        if self.poll_interval not in POLL_INTERVALS:
            raise ValueError(f"poll_interval must be one of {POLL_INTERVALS}")
        if not 0 <= self.long_running_hours <= 24:
            raise ValueError("long_running_hours must be between 0 and 24")
        if self.language != SYSTEM and self.language not in LANGUAGES:
            raise ValueError(f"language must be {SYSTEM!r} or one of {sorted(LANGUAGES)}")
        if self.contact_email and "@" not in self.contact_email:
            raise ValueError("contact_email is not an e-mail address")
        for name in ("default_customers_id", "default_projects_id", "default_services_id"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must not be negative")
        if bool(self.default_customers_id) != bool(self.default_services_id):
            raise ValueError("the default booking needs customer and service")
        if self.default_projects_id and not self.default_customers_id:
            raise ValueError("the default project needs a customer")
        if len(self.default_text) > 1000:
            raise ValueError("default_text is longer than 1000 characters")
        if self.panel_style not in PANEL_STYLES:
            raise ValueError(f"panel_style must be one of {PANEL_STYLES}")
        if self.modifier not in MODIFIERS:
            raise ValueError(f"modifier must be one of {MODIFIERS}")
        for name in ("modifier_click", "middle_click"):
            if getattr(self, name) not in CLICK_ACTIONS:
                raise ValueError(f"{name} must be one of {CLICK_ACTIONS}")
        if not 0 <= self.overtime_after_minutes <= 240:
            raise ValueError("overtime_after_minutes must be between 0 and 240")
        if not 0 <= self.overtime_repeat_minutes <= 480:
            raise ValueError("overtime_repeat_minutes must be between 0 and 480")

    def default_context(self) -> Context | None:
        """The default booking, or None if none is set."""
        if not self.default_customers_id or not self.default_services_id:
            return None
        return Context(
            customers_id=self.default_customers_id,
            services_id=self.default_services_id,
            projects_id=self.default_projects_id or None,
            text=self.default_text or None,
        )

    def ui(self) -> dict[str, Any]:
        """Settings the widget needs for the panel and the mouse."""
        keys = ("panel_style", "colorize", "modifier", "modifier_click", "middle_click")
        return {key: getattr(self, key) for key in keys} | {"overtime_color": self.overtime_color}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def updated(self, changes: dict[str, Any]) -> Settings:
        data = self.to_dict()
        for key, value in changes.items():
            if key == "schema_version" or key not in data:
                continue
            default = data[key]
            if isinstance(default, bool):
                data[key] = _parse_bool(key, value)
            elif isinstance(default, int):
                data[key] = int(value)
            else:
                data[key] = str(value).strip()
        result = Settings(**data)
        result.validate()
        return result


def _parse_bool(key: str, value: Any) -> bool:
    """Strict bool: ``bool("false")`` would be True, so strings are parsed."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1"):
            return True
        if text in ("false", "0"):
            return False
    raise ValueError(f"{key} must be true or false")


def _migrate(data: dict[str, Any]) -> dict[str, Any]:
    version = int(data.get("schema_version", 1))
    if version > SCHEMA_VERSION:
        log.warning("config schema %s is newer than supported %s", version, SCHEMA_VERSION)
    # Future migrations: if version < 2: ...
    data["schema_version"] = SCHEMA_VERSION
    return data


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)  # JSON strings are valid TOML strings


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class ConfigStore:
    def __init__(self, cfg_dir: Path | None = None, st_dir: Path | None = None) -> None:
        self.config_path = (cfg_dir or config_dir()) / "config.toml"
        self.state_path = (st_dir or state_dir()) / "state.json"

    # ------------------------------------------------------------- settings

    def load_settings(self) -> Settings:
        try:
            data = tomllib.loads(self.config_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return Settings()
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.warning("cannot read %s (%s), using defaults", self.config_path, exc)
            return Settings()
        try:
            return Settings().updated(_migrate(data))
        except (TypeError, ValueError) as exc:
            log.warning("invalid settings in %s (%s), using defaults", self.config_path, exc)
            return Settings()

    def save_settings(self, settings: Settings) -> None:
        lines = [f"# {APP_ID} settings – credentials are stored in the Secret Service"]
        lines += [f"{key} = {_toml_value(value)}" for key, value in settings.to_dict().items()]
        _atomic_write(self.config_path, "\n".join(lines) + "\n")

    # ------------------------------------------------------------- state

    def load_recent_contexts(self) -> list[Context]:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s (%s)", self.state_path, exc)
            return []
        contexts = []
        for item in data.get("recent_contexts", []):
            try:
                contexts.append(Context.from_dict(item))
            except (KeyError, TypeError, ValueError):
                continue
        return contexts[:MAX_RECENT_CONTEXTS]

    def save_recent_contexts(self, contexts: list[Context]) -> None:
        data = {
            "schema_version": SCHEMA_VERSION,
            "recent_contexts": [c.to_dict() for c in contexts[:MAX_RECENT_CONTEXTS]],
        }
        _atomic_write(self.state_path, json.dumps(data, indent=2) + "\n")


@dataclass
class RecentContexts:
    items: list[Context] = field(default_factory=list)

    def remember(self, context: Context) -> bool:
        """Move ``context`` to the front. Returns True if the list changed."""
        # The description text is not part of the context identity.
        plain = Context(
            context.customers_id,
            context.services_id,
            context.projects_id,
            context.subprojects_id,
        )
        new = [plain] + [c for c in self.items if c.key() != plain.key()]
        new = new[:MAX_RECENT_CONTEXTS]
        if new == self.items:
            return False
        self.items = new
        return True
