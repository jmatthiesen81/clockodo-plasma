# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import pytest

from clockodo_plasma import secret_store
from clockodo_plasma.secret_store import ATTRIBUTES, Credentials


class FakeItem:
    def __init__(self, collection: FakeCollection, attributes: dict[str, str], secret: bytes):
        self.collection = collection
        self.attributes = attributes
        self.secret = secret

    def delete(self) -> None:
        self.collection.items.remove(self)


class FakeCollection:
    def __init__(self, fail_create: bool = False) -> None:
        self.items: list[FakeItem] = []
        self.fail_create = fail_create

    def is_locked(self) -> bool:
        return False

    def search_items(self, attributes: dict[str, str]):
        for item in list(self.items):
            if all(item.attributes.get(k) == v for k, v in attributes.items()):
                yield item

    def create_item(self, label, attributes, secret, replace=False):
        if self.fail_create:
            raise RuntimeError("D-Bus error")
        if replace:
            for item in list(self.search_items(attributes)):
                item.delete()
        item = FakeItem(self, dict(attributes), secret)
        self.items.append(item)
        return item


class FakeConnection:
    def close(self) -> None:
        pass


@pytest.fixture
def collection(monkeypatch):
    coll = FakeCollection()
    monkeypatch.setattr(secret_store, "_connect", FakeConnection)
    monkeypatch.setattr(secret_store, "_collection", lambda conn: coll)
    return coll


def test_store_replaces_old_account(collection):
    secret_store._store_sync(Credentials("old@b.de", "old-key"))
    secret_store._store_sync(Credentials("new@b.de", "new-key"))
    items = list(collection.search_items(ATTRIBUTES))
    assert len(items) == 1
    assert items[0].attributes["account"] == "new@b.de"
    assert items[0].secret == b"new-key"


def test_failed_store_keeps_old_credentials(collection):
    secret_store._store_sync(Credentials("old@b.de", "old-key"))
    collection.fail_create = True
    with pytest.raises(RuntimeError):
        secret_store._store_sync(Credentials("new@b.de", "new-key"))
    items = list(collection.search_items(ATTRIBUTES))
    assert [item.secret for item in items] == [b"old-key"]
