# Findings

Risks, untested areas and open points as of version 0.1.0 (2026-11-19).

## Not tested yet

| Area                                     | Status                                                                                             |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Widget in a real Plasma session          | Not run yet; QML is only checked by `qmllint`. Layout, popup size and bindings need a manual test. |
| Real Clockodo account                    | API calls are tested only against mocks built from the OpenAPI spec.                               |
| KWallet / Secret Service                 | Not tested against a real provider; the container check covers only "no provider".                 |
| Screen lock and suspend on real hardware | Logic is unit-tested; the signals (`ActiveChanged`, clock jump) are not verified on CachyOS.       |
| `org.kde.plasma.workspace.dbus`          | Barely documented and not a promised stable API; Plasma updates can break the widget.              |

The [release checklist](operations.md#release-checklist) covers these points.

## Risks

- **D-Bus access:** every process of the user session can start or stop the clock through the interface. Accepted on purpose, because such a process could read the Secret Service anyway; the interface exposes no key and no raw API data.
- **API key scope:** a Clockodo API key has the full rights of the user. It is stored only in the Secret Service and never logged.
- **Firm-specific required fields:** Clockodo settings may require a project or a description on start. The widget shows Clockodo's error message, but cannot know these rules beforehand (unknown).
- **Subprojects** are not supported; contexts with a subproject are filtered out of the recent list.
- **Unpinned build inputs:** `Dockerfile.arch` uses `archlinux/archlinux:base-devel` without a digest, and the workflows use actions by major tag (`@v7`, `@v6`), while the plan recommends pinning by digest/commit SHA.
- **qmllint warnings:** all QML files access `root` from `main.qml` unqualified. This is common in plasmoids and works at runtime, but qmllint cannot check these bindings.

## Open points

Decided:

- The repository `https://github.com/jmatthiesen81/clockodo-plasma` is public; release 0.1.0 is published there.
- The web server for the pacman repository is a Debian server with Plesk (nginx proxy in front of Apache); publishing must run rsync as the subscription's system user (see [Operations – Web server](operations.md#web-server)).

| Point                    | Question                                                      |
| ------------------------ | ------------------------------------------------------------- |
| Klockodo                 | Check whether the existing GTK tool already covers the needs. |
| Secret Service on target | Active by default, or does `apiEnabled` need to be set?       |

## Roadmap

| Version   | Content                                                                                                              |
| --------- | -------------------------------------------------------------------------------------------------------------------- |
| 0.1.0     | Released on GitHub (2026-11-19), recipe ready; open: release checklist on CachyOS, then publishing.                  |
| 1.0.0     | All items of the release checklist fulfilled, accessibility checked in Plasma (keyboard, screen reader).             |
| After 1.0 | Plasma VM tests with GUI automation, subprojects, OAuth 2.0, absences, build provenance attestation, more languages. |

[Index](index.md) · [Deutsch](../de/findings.md)
