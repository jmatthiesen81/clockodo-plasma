# Development

Code layout, tests, tooling and conventions. Development works on any Linux with Python ≥ 3.12, `dbus-run-session` and Docker or Podman; CachyOS is only needed for the final test in Plasma.

## Layout

| Path                       | Content                                                                        |
| -------------------------- | ------------------------------------------------------------------------------ |
| `backend/clockodo_plasma/` | Daemon (see [Architecture](architecture.md#daemon-modules))                    |
| `plasmoid/`                | Widget metadata, QML and `translations.js`                                     |
| `packaging/`               | Start script, systemd unit, D-Bus service file, `arch/PKGBUILD` and `.install` |
| `scripts/`                 | Test, build, check, release helpers                                            |
| `tests/unit/`              | Unit tests with fakes for Clockodo, Secret Service and time                    |
| `tests/dbus/`              | Tests of the exported interface on a real private session bus                  |
| `Dockerfile.arch`          | Arch image for package builds and checks                                       |
| `.github/`                 | CI and release workflows, Dependabot                                           |
| `docs/`                    | Documentation (English and German)                                             |

## Tests and lint

```bash
scripts/test.sh                  # creates .venv on first run
scripts/test.sh -k switch        # extra arguments go to pytest
```

[test.sh](../../scripts/test.sh) runs `ruff check`, `ruff format --check`, [check-version.sh](../../scripts/check-version.sh) and `pytest` under `dbus-run-session`. Configuration is in [pyproject.toml](../../pyproject.toml) (ruff: line length 100, rules E, F, W, I, B, UP, SIM, ASYNC; pytest: `asyncio_mode = "auto"`, `pythonpath = ["backend"]`).

| Test file                                                           | Covers                                                                                                                                                               |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [test_service_actions.py](../../tests/unit/test_service_actions.py) | Booking safety: double click, lost response, clock running elsewhere, stale entry id, 404/409, switch, invalid context, 401, 429, network errors, suspend, reminders |
| [test_api.py](../../tests/unit/test_api.py)                         | Headers, request bodies, error mapping, unknown write outcome, pagination (respx mocks shaped after the OpenAPI spec)                                                |
| [test_time_calculator.py](../../tests/unit/test_time_calculator.py) | Day total, running clock counted once, overlaps, midnight, DST, time zones                                                                                           |
| [test_clock.py](../../tests/unit/test_clock.py)                     | Server time, suspend detection                                                                                                                                       |
| [test_config.py](../../tests/unit/test_config.py)                   | Settings, recent contexts, log redaction                                                                                                                             |
| [test_translations.py](../../tests/unit/test_translations.py)       | Completeness of all languages, placeholders, language resolution                                                                                                     |
| [test_dbus_interface.py](../../tests/dbus/test_dbus_interface.py)   | Methods and signal over D-Bus, no key in answers, invalid input                                                                                                      |

Tests are deterministic: time comes from a fake clock, Clockodo from an in-memory fake ([conftest.py](../../tests/conftest.py)). The QML is only checked by `qmllint` in the package check; there are no automated UI tests.

## Running the daemon from the checkout

```bash
PYTHONPATH=backend .venv/bin/python -m clockodo_plasma.main --debug
```

It takes the real bus name on your session bus, so stop an installed daemon first (`systemctl --user stop clockodo-plasma`).

## Translations

The widget does not use Plasma's `i18n()`, because that always follows the system language. Texts go through `root.tr("English text", arg1, arg2)` and `root.trp(singular, plural, n)` in QML; translations are in [translations.js](../../plasmoid/contents/ui/translations.js), keyed by the English text. The daemon's texts are in [messages.py](../../backend/clockodo_plasma/messages.py).

To add a language:

1. Add code and native name to `LANGUAGES` in `messages.py`.
2. Add the language to every entry of `MESSAGES`.
3. Add a catalog for it in `translations.js`.

`test_translations.py` fails while a text is missing, a catalog entry is unused or placeholders differ. Both catalogs currently assume the plural rule "one for n = 1, other otherwise".

## Conventions

- Version numbers are set only by `scripts/release.sh`; `check-version.sh` verifies them in tests and in the release workflow.
- Changes go under `## [Unreleased]` in `CHANGELOG.md` (Keep a Changelog).
- Every source file starts with `SPDX-License-Identifier: MPL-2.0`.
- D-Bus methods take and return strings (JSON for structures).
- No write call to Clockodo may be retried; new actions must follow the rules in [Architecture – Booking safety](architecture.md#booking-safety) and get tests in `test_service_actions.py`.

## CI

[ci.yml](../../.github/workflows/ci.yml) runs on every push except release tags and on pull requests: `scripts/test.sh` on Ubuntu with Python 3.14, and `scripts/build-package.sh --check`; the built package is kept as a workflow artifact for 7 days. Dependabot updates GitHub Actions and pip dependencies weekly.

[Index](index.md) · [Deutsch](../de/development.md)
