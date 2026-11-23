# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import logging

import pytest

from clockodo_plasma.api import Context
from clockodo_plasma.config import ConfigStore, RecentContexts, Settings
from clockodo_plasma.logutil import RedactingFilter, register_secret
from clockodo_plasma.secret_store import Credentials


def test_settings_roundtrip(tmp_path):
    store = ConfigStore(tmp_path / "c", tmp_path / "s")
    assert store.load_settings() == Settings()
    settings = Settings().updated({"poll_interval": 120, "contact_email": "a@b.de"})
    store.save_settings(settings)
    assert store.load_settings() == settings
    assert "api" not in store.config_path.read_text().lower()


def test_invalid_settings_rejected():
    with pytest.raises(ValueError):
        Settings().updated({"poll_interval": 7})
    with pytest.raises(ValueError):
        Settings().updated({"contact_email": "nope"})


def test_bool_settings_are_parsed_strictly():
    assert Settings().updated({"colorize": False}).colorize is False
    assert Settings().updated({"colorize": "false"}).colorize is False
    assert Settings().updated({"colorize": "True"}).colorize is True
    assert Settings().updated({"colorize": 0}).colorize is False
    with pytest.raises(ValueError):
        Settings().updated({"colorize": "maybe"})
    with pytest.raises(ValueError):
        Settings().updated({"colorize": 2})


def test_broken_file_falls_back_to_defaults(tmp_path):
    store = ConfigStore(tmp_path / "c", tmp_path / "s")
    store.config_path.parent.mkdir(parents=True)
    store.config_path.write_text("poll_interval = [")
    assert store.load_settings() == Settings()


def test_unknown_keys_are_ignored(tmp_path):
    store = ConfigStore(tmp_path / "c", tmp_path / "s")
    store.config_path.parent.mkdir(parents=True)
    store.config_path.write_text("schema_version = 1\npoll_interval = 30\nfuture_option = 1\n")
    assert store.load_settings().poll_interval == 30


def test_recent_contexts():
    recent = RecentContexts()
    for customer in range(1, 8):
        recent.remember(Context(customer, 10))
    assert len(recent.items) == 5
    assert recent.items[0].customers_id == 7
    assert recent.remember(Context(5, 10, text="ignored")) is True
    assert recent.items[0].customers_id == 5
    assert recent.items[0].text is None
    assert recent.remember(Context(5, 10)) is False


def test_recent_contexts_persist(tmp_path):
    store = ConfigStore(tmp_path / "c", tmp_path / "s")
    store.save_recent_contexts([Context(1, 10, 5)])
    assert store.load_recent_contexts() == [Context(1, 10, 5)]


def test_credentials_repr_hides_key():
    assert "geheim" not in repr(Credentials("a@b.de", "geheim"))


def test_log_redaction():
    register_secret("super-secret-key")
    record = logging.LogRecord("x", logging.INFO, "", 0, "key=%s", ("super-secret-key",), None)
    RedactingFilter().filter(record)
    assert "super-secret-key" not in record.getMessage()
