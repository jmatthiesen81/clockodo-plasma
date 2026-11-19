# Clockodo Plasma

Unofficial KDE Plasma 6 panel widget for [Clockodo](https://www.clockodo.com/) time tracking.
It shows today's work time (`HH:MM`) in the panel – green while the clock runs, orange while it is
stopped, red over the daily target. A click opens a popup to start, stop or switch the clock with
an explicitly chosen customer › project › service; Ctrl + click, a middle click or the context
menu start a configurable default booking or stop the clock directly.

Clockodo stays the only source of truth: no local database, no offline bookings, and the
widget never books anything without a click. Write calls are never retried; before a start
the clock is read fresh, so a clock started on another device is never replaced silently.

## Quick facts

|              |                                                                                               |
| ------------ | --------------------------------------------------------------------------------------------- |
| Target       | CachyOS / Arch Linux with KDE Plasma ≥ 6.4                                                    |
| Widget       | QML plasmoid `io.github.jmatthiesen81.clockodoplasma`                                         |
| Daemon       | Python ≥ 3.12 (asyncio, httpx, dbus-fast, secretstorage), systemd user unit, D-Bus activation |
| D-Bus name   | `io.github.jmatthiesen81.ClockodoPlasma` (JSON strings in and out)                            |
| Credentials  | Secret Service (KWallet), never in files                                                      |
| Languages    | English, German; chosen in the settings (default: system language, else English)              |
| Distribution | Arch package (`arch=any`) from an own pacman repository; GitHub releases carry the source     |
| License      | [MPL-2.0](LICENSE)                                                                            |

## Quick start

```bash
sudo pacman -Syu clockodo-plasma          # from the pacman repository, or:
scripts/build-package.sh --check          # local build in the Arch container (Docker/Podman)
sudo pacman -U dist/clockodo-plasma-*-any.pkg.tar.zst
```

Then *Add Widgets…* → *Clockodo Time Tracking*, click it and enter your Clockodo e-mail and
API key (Clockodo → *Personal data*). Details: [Setup](docs/en/setup.md).

Development: `scripts/test.sh` runs ruff, the version check and all tests (incl. D-Bus tests);
releases are made with `scripts/release.sh X.Y.Z` (tags without `v`), see [Operations](docs/en/operations.md#release).

## Project structure

| Path         | Content                                                             |
| ------------ | ------------------------------------------------------------------- |
| `backend/`   | Daemon (`clockodo_plasma`): API client, service, poller, D-Bus      |
| `plasmoid/`  | Widget metadata, QML and `translations.js`                          |
| `packaging/` | Start script, systemd and D-Bus service files, development PKGBUILD |
| `scripts/`   | Tests, package build/check, release helpers                         |
| `tests/`     | Unit tests and D-Bus tests                                          |
| `docs/`      | Documentation in English and German                                 |

## Documentation

| Topic           | English                                       | Deutsch                                      |
| --------------- | --------------------------------------------- | -------------------------------------------- |
| Index           | [index](docs/en/index.md)                     | [Index](docs/de/index.md)                    |
| Overview        | [overview](docs/en/overview.md)               | [Überblick](docs/de/overview.md)             |
| Architecture    | [architecture](docs/en/architecture.md)       | [Architektur](docs/de/architecture.md)       |
| Setup           | [setup](docs/en/setup.md)                     | [Einrichtung](docs/de/setup.md)              |
| Configuration   | [configuration](docs/en/configuration.md)     | [Konfiguration](docs/de/configuration.md)    |
| Operations      | [operations](docs/en/operations.md)           | [Betrieb](docs/de/operations.md)             |
| Development     | [development](docs/en/development.md)         | [Entwicklung](docs/de/development.md)        |
| Troubleshooting | [troubleshooting](docs/en/troubleshooting.md) | [Fehlerbehebung](docs/de/troubleshooting.md) |
| Findings        | [findings](docs/en/findings.md)               | [Befunde](docs/de/findings.md)               |
| Changes         | [CHANGELOG.md](CHANGELOG.md)                  |                                              |

## Important notes

- Version 0.1.0 has not yet been tested in a real Plasma session against a real Clockodo account ([findings](docs/en/findings.md)).
- Not affiliated with Clockodo GmbH; "Clockodo" is used only to describe what the widget works with.
- Uninstalling leaves your settings, the KWallet entry and the widget in the panel in place; `pacman` prints how to remove them.
