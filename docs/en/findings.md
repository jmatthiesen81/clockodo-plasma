# Findings

Risks, untested areas and open points as of version 0.2.0 (2026-11-19).

## Not tested yet

| Area                                     | Status                                                                                                                                                                                                                                          |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Widget in a real Plasma session          | 0.2.0 runs in a real Plasma session on CachyOS (2026-11-23): popup, credentials form and settings as well as the 0.2.0 features (panel styles, quick start/stop, context menu, configuration dialog, overtime warning with *Stop* button) work. |
| Real Clockodo account                    | 0.1.1 read a real account (user, today's total, customers, projects, services). Start, stop and switch are confirmed against a real account (2026-11-23). The daily target (day report) runs against the real account with 0.2.0.               |
| KWallet / Secret Service                 | Storing and reading the credentials works with KWallet on CachyOS; locked wallet and "no provider" are only covered by tests.                                                                                                                   |
| Screen lock and suspend on real hardware | Logic is unit-tested; the signals (`ActiveChanged`, clock jump) are not verified on CachyOS.                                                                                                                                                    |
| `org.kde.plasma.workspace.dbus`          | Barely documented and not a promised stable API; Plasma updates can break the widget.                                                                                                                                                           |

The [release checklist](operations.md#release-checklist) covers these points.

## Risks

- **D-Bus access:** every process of the user session can start or stop the clock through the interface. Accepted on purpose, because such a process could read the Secret Service anyway; the interface exposes no key and no raw API data.
- **API key scope:** a Clockodo API key has the full rights of the user. It is stored only in the Secret Service and never logged.
- **Firm-specific required fields:** Clockodo settings may require a project or a description on start. The widget shows Clockodo's error message, but cannot know these rules beforehand (unknown).
- **Subprojects** are not supported; contexts with a subproject are filtered out of the recent list.
- **Build inputs:** The GitHub Actions are pinned to commit SHAs (with a version comment; Dependabot keeps them up to date). `Dockerfile.arch` uses `archlinux/archlinux:base-devel` without a digest on purpose: the image runs `pacman -Syu` right away and fetches the current packages anyway, so a digest would hardly make the build more reproducible. The image is only used for building and checking and does not end up in the package.
- **qmllint warnings:** the QML files access `root` (from `main.qml` or the configuration page) unqualified. This is common in plasmoids and works at runtime, but qmllint cannot check these bindings. It also missed a wrong property name (`separator` instead of `isSeparator`) that stopped the widget from loading; only a run in `plasmoidviewer` found it, so a runtime check belongs in every release check.
- **D-Bus module quirks:** in 0.1.0 every call with arguments failed because the module expects the argument signature as one struct (`(ss)`, not `ss`); this is not documented and could change again.

## Open points

Decided:

- The repository `https://github.com/jmatthiesen81/clockodo-plasma` is public; releases 0.1.0 and 0.1.1 are published there.
- The web server for the pacman repository is a Debian server with Plesk (nginx proxy in front of Apache); publishing must run rsync as the subscription's system user (see [Operations – Web server](operations.md#web-server)).

| Point    | Question                                                      |
| -------- | ------------------------------------------------------------- |
| Klockodo | Check whether the existing GTK tool already covers the needs. |

## Roadmap

| Version   | Content                                                                                                                                                                                   |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0.1.0     | Released on GitHub (2026-11-19), recipe ready.                                                                                                                                            |
| 0.1.1     | D-Bus fix and popup layout; first run on CachyOS with a real account.                                                                                                                     |
| 0.2.0     | Default booking with quick start/stop, context menu, daily target, panel styles, configuration dialog; tested on CachyOS with a real account; open: the release checklist and publishing. |
| 1.0.0     | All items of the release checklist fulfilled, accessibility checked in Plasma (keyboard, screen reader).                                                                                  |
| After 1.0 | Plasma VM tests with GUI automation, subprojects, OAuth 2.0, absences, build provenance attestation, more languages.                                                                      |

[Index](index.md) · [Deutsch](../de/findings.md)
