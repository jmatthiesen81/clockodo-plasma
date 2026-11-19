# Entwicklung

Code-Layout, Tests, Werkzeuge und Konventionen. Die Entwicklung funktioniert auf jedem Linux mit Python ≥ 3.12, `dbus-run-session` und Docker oder Podman; CachyOS wird nur für den abschließenden Test in Plasma benötigt.

## Aufbau

| Pfad                       | Inhalt                                                                         |
| -------------------------- | ------------------------------------------------------------------------------ |
| `backend/clockodo_plasma/` | Daemon (siehe [Architektur](architecture.md#daemon-module))                    |
| `plasmoid/`                | Widget-Metadaten, QML und `translations.js`                                    |
| `packaging/`               | Startskript, systemd-Unit, D-Bus-Service-Datei, `arch/PKGBUILD` und `.install` |
| `scripts/`                 | Hilfsskripte für Test, Build, Prüfung, Release                                 |
| `tests/unit/`              | Unit-Tests mit Fakes für Clockodo, Secret Service und Zeit                     |
| `tests/dbus/`              | Tests der exportierten Schnittstelle auf einem echten privaten Session-Bus     |
| `Dockerfile.arch`          | Arch-Image für Paket-Builds und -Prüfungen                                     |
| `.github/`                 | CI- und Release-Workflows, Dependabot                                          |
| `docs/`                    | Dokumentation (Englisch und Deutsch)                                           |

## Tests und Lint

```bash
scripts/test.sh                  # legt beim ersten Lauf .venv an
scripts/test.sh -k switch        # zusätzliche Argumente gehen an pytest
```

[test.sh](../../scripts/test.sh) führt `ruff check`, `ruff format --check`, [check-version.sh](../../scripts/check-version.sh) und `pytest` unter `dbus-run-session` aus. Die Konfiguration steht in [pyproject.toml](../../pyproject.toml) (ruff: Zeilenlänge 100, Regeln E, F, W, I, B, UP, SIM, ASYNC; pytest: `asyncio_mode = "auto"`, `pythonpath = ["backend"]`).

| Testdatei                                                           | Deckt ab                                                                                                                                                                                    |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [test_service_actions.py](../../tests/unit/test_service_actions.py) | Buchungssicherheit: Doppelklick, verlorene Antwort, anderswo laufende Uhr, veraltete Eintrags-ID, 404/409, Wechsel, ungültiger Kontext, 401, 429, Netzwerkfehler, Ruhezustand, Erinnerungen |
| [test_api.py](../../tests/unit/test_api.py)                         | Header, Request-Bodys, Fehlerabbildung, unbekanntes Schreibergebnis, Paginierung (respx-Mocks nach der OpenAPI-Spezifikation)                                                               |
| [test_time_calculator.py](../../tests/unit/test_time_calculator.py) | Tagessumme, laufende Uhr einmal gezählt, Überlappungen, Mitternacht, Sommerzeit, Zeitzonen                                                                                                  |
| [test_clock.py](../../tests/unit/test_clock.py)                     | Serverzeit, Erkennung des Ruhezustands                                                                                                                                                      |
| [test_config.py](../../tests/unit/test_config.py)                   | Einstellungen, zuletzt verwendete Kontexte, Log-Schwärzung                                                                                                                                  |
| [test_translations.py](../../tests/unit/test_translations.py)       | Vollständigkeit aller Sprachen, Platzhalter, Sprachauflösung                                                                                                                                |
| [test_dbus_interface.py](../../tests/dbus/test_dbus_interface.py)   | Methoden und Signal über D-Bus, kein Schlüssel in Antworten, ungültige Eingaben                                                                                                             |

Die Tests sind deterministisch: Die Zeit kommt von einer Fake-Uhr, Clockodo von einem In-Memory-Fake ([conftest.py](../../tests/conftest.py)). Das QML wird nur in der Paketprüfung mit `qmllint` geprüft; automatisierte UI-Tests gibt es nicht.

## Daemon aus dem Checkout starten

```bash
PYTHONPATH=backend .venv/bin/python -m clockodo_plasma.main --debug
```

Er belegt den echten Bus-Namen auf dem Session-Bus, daher zuerst einen installierten Daemon stoppen (`systemctl --user stop clockodo-plasma`).

## Übersetzungen

Das Widget verwendet nicht das `i18n()` von Plasma, weil dieses stets der Systemsprache folgt. Texte laufen in QML über `root.tr("English text", arg1, arg2)` und `root.trp(singular, plural, n)`; die Übersetzungen stehen in [translations.js](../../plasmoid/contents/ui/translations.js), geordnet nach dem englischen Text. Die Texte des Daemons stehen in [messages.py](../../backend/clockodo_plasma/messages.py).

Eine Sprache hinzufügen:

1. Code und nativen Namen in `LANGUAGES` in `messages.py` ergänzen.
2. Die Sprache zu jedem Eintrag von `MESSAGES` hinzufügen.
3. Einen Katalog dafür in `translations.js` anlegen.

`test_translations.py` schlägt fehl, solange ein Text fehlt, ein Katalogeintrag ungenutzt ist oder Platzhalter abweichen. Beide Kataloge setzen derzeit die Pluralregel „one für n = 1, sonst other“ voraus.

## Branches

Das Projekt arbeitet trunk-basiert mit einem einzigen dauerhaften Branch, **`canon`** (der Standard-Branch):

- Feature-Branches (`feat/<thema>`, `fix/<thema>`, `chore/<thema>`, …) zweigen von `canon` ab und werden dorthin zurückgeführt.
- Releases sind nur Tags auf `canon` (`0.2.0`, `0.2.1`, …, ohne Präfix `v`); für ein Release entsteht kein Branch.
- Eine alte Release-Linie wird nur gepflegt, wenn es wirklich nötig ist: Der Branch entsteht aus dem Tag (`git switch -c 0.1 0.1.1`), der Fix wird dort committet und getaggt (`0.1.2`). `release.sh` akzeptiert einen solchen Branch für Versionen seiner Linie und weist bei jedem anderen Branch darauf hin.

Der Name folgt der Metapher aus dem office-attendance-bot (ADR 0004): Feature-Branches sind Ideen, die noch nicht offiziell sind, das Mergen macht sie zum Kanon, und ein Release-Tag ist eine veröffentlichte Ausgabe des Kanons. Bis 0.1.1 nutzte das Projekt einen Versions-Branch `1.0`; ein bestehender Klon stellt einmalig so um:

```bash
git branch -m 1.0 canon
git fetch origin --prune
git branch -u origin/canon canon
git remote set-head origin -a
```

## Konventionen

- Versionsnummern werden nur von `scripts/release.sh` gesetzt; `check-version.sh` prüft sie in den Tests und im Release-Workflow.
- Änderungen kommen unter `## [Unreleased]` in `CHANGELOG.md` (Keep a Changelog).
- Jede Quelldatei beginnt mit `SPDX-License-Identifier: MPL-2.0`.
- D-Bus-Methoden nehmen Strings entgegen und liefern Strings zurück (JSON für Strukturen).
- Kein Schreibaufruf an Clockodo darf wiederholt werden; neue Aktionen müssen den Regeln in [Architektur – Buchungssicherheit](architecture.md#buchungssicherheit) folgen und Tests in `test_service_actions.py` erhalten.

## CI

[ci.yml](../../.github/workflows/ci.yml) läuft bei jedem Push außer bei Release-Tags und bei Pull Requests: `scripts/test.sh` auf Ubuntu mit Python 3.14 sowie `scripts/build-package.sh --check`; das gebaute Paket bleibt 7 Tage als Workflow-Artefakt erhalten. Dependabot aktualisiert GitHub Actions und pip-Abhängigkeiten wöchentlich.

[Index](index.md) · [English](../en/development.md)
