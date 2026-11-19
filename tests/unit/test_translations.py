# SPDX-License-Identifier: MPL-2.0
"""Every user-facing text exists in every supported language."""

from __future__ import annotations

import json
import re
from pathlib import Path

from clockodo_plasma import messages
from clockodo_plasma.config import Settings

UI = Path(__file__).resolve().parents[2] / "plasmoid" / "contents" / "ui"
CONFIG = UI.parent / "config"

# root.tr("text") / tr("text") and root.trp("singular", "plural", n)
STRING = r'"((?:[^"\\]|\\.)*)"'
TR = re.compile(r"\btr\(\s*" + STRING)
TRP = re.compile(r"\btrp\(\s*" + STRING + r"\s*,\s*" + STRING)


def unescape(text: str) -> str:
    return json.loads(f'"{text}"')


def catalogs() -> dict[str, dict]:
    source = (UI / "translations.js").read_text(encoding="utf-8")
    start = source.index("const catalogs = ") + len("const catalogs = ")
    end = source.index("};", start) + 1
    return json.loads(source[start:end])


def used_strings() -> tuple[set[str], set[str]]:
    singles: set[str] = set()
    plurals: set[str] = set()
    for qml in [*UI.glob("*.qml"), *CONFIG.glob("*.qml")]:
        text = qml.read_text(encoding="utf-8")
        singles |= {unescape(m) for m in TR.findall(text)}
        plurals |= {f"{unescape(a)}|{unescape(b)}" for a, b in TRP.findall(text)}
    return singles, plurals


def test_no_kde_i18n_left():
    for qml in UI.glob("*.qml"):
        assert "i18n" not in qml.read_text(encoding="utf-8"), qml.name


def test_widget_catalogs_are_complete():
    singles, plurals = used_strings()
    assert singles and plurals
    cats = catalogs()
    for language in messages.LANGUAGES:
        if language == "en":
            continue
        catalog = cats[language]
        missing = sorted(s for s in singles if s not in catalog)
        missing += sorted(p for p in plurals if p not in catalog)
        assert not missing, f"{language}: {missing}"
        unused = sorted(k for k in catalog if k not in singles and k not in plurals)
        assert not unused, f"{language} has unused entries: {unused}"


def test_widget_and_daemon_languages_agree():
    assert set(catalogs()) | {"en"} == set(messages.LANGUAGES)


def test_daemon_messages_are_complete():
    for key, entry in messages.MESSAGES.items():
        assert set(entry) == set(messages.LANGUAGES), key


def test_placeholders_match():
    for key, entry in messages.MESSAGES.items():
        names = {frozenset(re.findall(r"{(\w+)}", text)) for text in entry.values()}
        assert len(names) == 1, key
    for language, catalog in catalogs().items():
        for source, translated in catalog.items():
            forms = translated if isinstance(translated, list) else [translated]
            for form in forms:
                assert set(re.findall(r"%\d", form)) == set(re.findall(r"%\d", source)), (
                    language,
                    source,
                )


def test_system_language_resolution():
    resolve = messages.system_language
    assert resolve({"LANG": "de_DE.UTF-8"}) == "de"
    assert resolve({"LANGUAGE": "fr:de", "LANG": "fr_FR.UTF-8"}) == "de"
    assert resolve({"LANG": "fr_FR.UTF-8"}) == "en"
    assert resolve({"LANG": "C.UTF-8"}) == "en"
    assert resolve({}) == "en"
    assert messages.resolve_language("de", {"LANG": "en_US.UTF-8"}) == "de"
    assert messages.resolve_language("system", {"LC_MESSAGES": "de_AT"}) == "de"


def test_language_setting_is_validated():
    assert Settings().language == "system"
    assert Settings().updated({"language": "de"}).language == "de"
    try:
        Settings().updated({"language": "xx"})
    except ValueError:
        pass
    else:
        raise AssertionError("invalid language accepted")


def test_switching_language():
    try:
        messages.set_language("de")
        assert messages.t("stopped") == "Uhr gestoppt."
        messages.set_language("en")
        assert messages.t("stopped") == "Clock stopped."
        messages.set_language("xx")
        assert messages.current_language() == "en"
    finally:
        messages.set_language(messages.resolve_language("system"))
