# Changelog

All notable changes to Clockodo Plasma are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-11-23

### Fixed

- Saving new credentials deleted the stored API key before writing the new one; if writing failed, the old credentials were lost. The new item is now stored first and older items are removed afterwards.
- Boolean settings sent as strings were read with `bool()`, so `"false"` became `true`. They are now parsed strictly, and invalid values are rejected.

### Changed

- CI runs the tests on Python 3.12 (oldest supported version) as well as 3.14.
- GitHub Actions are pinned to commit SHAs instead of movable version tags.

## [0.2.0] - 2026-11-19

### Added

- **Default booking and quick start/stop:** a default customer › project › service (with optional description) set in the configuration. Key + left click (default Ctrl, configurable), middle click or the context menu start it directly or stop the clock shown in the panel; what each click does is configurable (quick start/stop, open the selection, nothing). Without a default booking the selection opens. A clock running elsewhere is never replaced, and failures are shown as a notification.
- **Context menu:** status line, quick start/stop, start or switch with selection, switch to the default booking, and the recently used contexts.
- **Daily target:** read once per day from Clockodo's day report (public holidays and absences included). The ring shows the progress; over the target the time turns red, and an optional notification with a *Stop* button warns (tolerance and repeat interval configurable).
- **Panel styles:** ring (default), stopwatch or pill; green while running, orange while stopped, red over the target (theme colours, can be switched off).
- **Configuration dialog** with the pages Default booking, Controls, Reminders, General and Account (right-click → *Configure…* or the gear icon in the popup).

### Changed

- Redesigned popup: status with coloured total and target, quick start with the default booking, recently used contexts as one-click shortcuts, "Booked on" card with Stop and Switch, and a separate "Start/Switch with selection" view with labels above the fields and "Remember as default booking".
- The settings moved from the popup to the Plasma configuration dialog.
- Development is trunk-based on the branch `canon` instead of the version branch `1.0`; releases are tags on `canon` (see docs/en/development.md, "Branches").

## [0.1.1] - 2026-11-19

### Fixed

- Every widget call with arguments (save credentials, start, stop, switch, save settings) failed with `… with signature "" could not be found`: the Plasma D-Bus module expects the in-arguments as one struct signature (`(ss)`), not `ss`.
- The popup cut off the settings at the bottom and on the right: the header was not counted in its height, and the long reminder text widened the content. The views now scroll vertically, and long texts wrap.

## [0.1.0] - 2026-11-19

### Added

- **Panel widget for KDE Plasma 6.4+:** play/pause symbol and today's work time (`HH:MM`); a click opens the popup and synchronises with Clockodo right away.
- **Start, stop and switch** from the popup with an explicitly chosen booking context (customer › project › service), the five recently used contexts as shortcuts and an optional description.
- **Booking safety:** write calls are never retried; before a start the clock is read fresh and a clock running elsewhere is never replaced silently; stop uses the entry id; a lost response leads to a re-read instead of a second booking; one action at a time.
- **Background service** (`clockodo-plasma-daemon`, systemd user unit with D-Bus activation): one poller for all widget instances, configurable interval (off, 30 s, 1, 2, 5 min) with back-off on errors, detection of suspend/resume and day changes.
- Today's total from Clockodo's work times, computed for the Clockodo time zone of the user and advanced locally from the server time.
- API key stored in the Secret Service (KWallet); clear states for a locked wallet and a rejected key.
- Reminders: notification when the screen is locked while the clock runs, after resume, and optionally after a configurable number of hours.
- User interface in English and German.
- Licensed under the Mozilla Public License 2.0.
- Arch Linux package (`arch=any`) with the Python code outside `site-packages`, so Python minor updates do not break it.

### Changed

- CI and release workflows use `actions/setup-python` v7.

[Unreleased]: https://github.com/jmatthiesen81/clockodo-plasma/compare/0.2.1...HEAD
[0.2.1]: https://github.com/jmatthiesen81/clockodo-plasma/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/jmatthiesen81/clockodo-plasma/compare/0.1.1...0.2.0
[0.1.1]: https://github.com/jmatthiesen81/clockodo-plasma/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/jmatthiesen81/clockodo-plasma/releases/tag/0.1.0
