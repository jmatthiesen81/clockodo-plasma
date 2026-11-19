# Architecture

How the daemon and the widget are built, how they talk to each other and to Clockodo, and which rules protect against wrong bookings.

## Design decisions

| Decision                                                    | Reason                                                                                                                                                                                                                                                           |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Widget plus daemon instead of a pure QML widget             | QML has no Secret Service API, so the API key would end up in plain text in `plasma-org.kde.plasma.desktop-appletsrc`; `Plasmoid.configuration` is per widget instance, so every instance would poll on its own; logic in a daemon can be tested without Plasma. |
| Python daemon instead of a C++ plugin                       | A C++ plugin (e.g. with qtkeychain) would tie the package to an architecture and need rebuilds on every Qt/KF update in the own repository.                                                                                                                      |
| asyncio, httpx, dbus-fast, secretstorage instead of PySide6 | No Qt runtime in the background; exporting objects with PySide6/QtDBus is cumbersome. All libraries are in Arch `extra`.                                                                                                                                         |
| Plasma ≥ 6.4                                                | `SignalWatcher` of `org.kde.plasma.workspace.dbus` exists only from 6.4 (`asyncCall` from 6.2). Without it the widget would have to poll the daemon.                                                                                                             |
| JSON strings over D-Bus                                     | Trivial marshalling between Python and QML; no int64 precision loss in JavaScript.                                                                                                                                                                               |
| `/v2/workTimes` for today's total                           | Clockodo merges overlaps and leaves out lump sums; `/v2/entries` is paginated, contains lump sums and possibly entries of other users.                                                                                                                           |
| Switch as one `POST /v2/clock`                              | Clockodo stops the running entry itself: no gap, no "stopped, start failed".                                                                                                                                                                                     |
| D-Bus activation through the systemd unit                   | No autostart entry; `SystemdService=` is required because Arch uses dbus-broker.                                                                                                                                                                                 |
| Code in `/usr/lib/clockodo-plasma`                          | A Python minor update on Arch (e.g. 3.13 → 3.14) does not break the package, which would happen with `site-packages`.                                                                                                                                            |
| Own translation catalog                                     | Plasma's `i18n()` always follows the system language and cannot be switched per widget.                                                                                                                                                                          |
| Recent contexts remembered locally                          | Avoids extra `/v2/entries` requests and rate-limit pressure; only ids are stored.                                                                                                                                                                                |

## Components

| Part              | Location                                                                                                                   | Technology                                                                 |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Daemon            | [backend/clockodo_plasma/](../../backend/clockodo_plasma/)                                                                 | Python ≥ 3.12, asyncio, httpx, dbus-fast, secretstorage                    |
| Widget            | [plasmoid/](../../plasmoid/)                                                                                               | QML, Plasma 6 (`PlasmoidItem`), Kirigami, `org.kde.plasma.workspace.dbus`  |
| Start script      | [packaging/clockodo-plasma-daemon](../../packaging/clockodo-plasma-daemon)                                                 | `/bin/sh`, runs `python3 -I` with the code from `/usr/lib/clockodo-plasma` |
| systemd user unit | [packaging/clockodo-plasma.service](../../packaging/clockodo-plasma.service)                                               | `Type=dbus`, `Restart=on-failure`, no `[Install]`                          |
| D-Bus activation  | [packaging/io.github.jmatthiesen81.ClockodoPlasma.service](../../packaging/io.github.jmatthiesen81.ClockodoPlasma.service) | `SystemdService=clockodo-plasma.service`                                   |

## Daemon modules

| Module                                                                 | Responsibility                                                                                           |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [main.py](../../backend/clockodo_plasma/main.py)                       | Entry point: connects to the session bus, initialises, takes the bus name, runs until SIGTERM/disconnect |
| [api.py](../../backend/clockodo_plasma/api.py)                         | Clockodo HTTP client, required headers, error mapping, data classes                                      |
| [service.py](../../backend/clockodo_plasma/service.py)                 | Orchestration: sync, start/stop/switch with the safety rules, contexts, credentials, settings, reminders |
| [poller.py](../../backend/clockodo_plasma/poller.py)                   | Poll loop (interval/back-off, merged triggers) and one-second tick                                       |
| [state.py](../../backend/clockodo_plasma/state.py)                     | Published state and its JSON form                                                                        |
| [time_calculator.py](../../backend/clockodo_plasma/time_calculator.py) | Day bounds (DST-safe, in UTC) and today's total from work time intervals                                 |
| [clock.py](../../backend/clockodo_plasma/clock.py)                     | Server-anchored time and detection of wall clock jumps (suspend)                                         |
| [dbus_interface.py](../../backend/clockodo_plasma/dbus_interface.py)   | Exported D-Bus interface                                                                                 |
| [secret_store.py](../../backend/clockodo_plasma/secret_store.py)       | Secret Service access in a worker thread                                                                 |
| [notifications.py](../../backend/clockodo_plasma/notifications.py)     | Desktop notifications and screen lock monitoring                                                         |
| [config.py](../../backend/clockodo_plasma/config.py)                   | Settings (TOML) and recent contexts (JSON), validation, schema version                                   |
| [messages.py](../../backend/clockodo_plasma/messages.py)               | Texts of the daemon in all languages, language resolution                                                |
| [logutil.py](../../backend/clockodo_plasma/logutil.py)                 | Logging to stderr/journald with redaction of registered secrets                                          |

## Widget files

| File                                                                              | Content                                                                |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [metadata.json](../../plasmoid/metadata.json)                                     | Plugin id `io.github.jmatthiesen81.clockodoplasma`, version, license   |
| [main.qml](../../plasmoid/contents/ui/main.qml)                                   | State, D-Bus calls, signal and service watcher, tooltip, `tr()`        |
| [CompactRepresentation.qml](../../plasmoid/contents/ui/CompactRepresentation.qml) | Panel: icon, `HH:MM`, warning icon                                     |
| [FullRepresentation.qml](../../plasmoid/contents/ui/FullRepresentation.qml)       | Popup with messages and the views tracking/credentials/locked/settings |
| [ContextPicker.qml](../../plasmoid/contents/ui/ContextPicker.qml)                 | Recent contexts and customer/project/service selection                 |
| [CredentialsForm.qml](../../plasmoid/contents/ui/CredentialsForm.qml)             | E-mail and API key                                                     |
| [SettingsView.qml](../../plasmoid/contents/ui/SettingsView.qml)                   | Language, interval, reminders, contact e-mail                          |
| [translations.js](../../plasmoid/contents/ui/translations.js)                     | Widget translations keyed by the English text                          |

The widget keeps a local copy of the state and advances the total every 10 seconds while the clock runs; the daemon corrects it every minute. If no signal arrives, the widget re-reads the state every 2 minutes.

## D-Bus interface

Bus name, interface: `io.github.jmatthiesen81.ClockodoPlasma`; object path: `/io/github/jmatthiesen81/ClockodoPlasma`. All arguments and results are strings; structured data is JSON. This keeps marshalling between Python and QML trivial and avoids int64 precision loss in JavaScript (entry ids are passed as strings).

| Member                                     | Result / purpose                                                                |
| ------------------------------------------ | ------------------------------------------------------------------------------- |
| `GetState() → s`                           | Current state as JSON (see below)                                               |
| `Refresh()`                                | Requests an immediate sync                                                      |
| `ListContexts() → s`                       | Active customers, projects, services and the recently used contexts             |
| `Start(s context) → s`                     | `{"ok", "message"}`; context `{customers_id, projects_id?, services_id, text?}` |
| `Stop(s entry_id) → s`                     | Stops exactly this entry                                                        |
| `Switch(s context, s entry_id) → s`        | Replaces the running entry `entry_id` with a new context                        |
| `SetCredentials(s email, s api_key) → s`   | Checks with Clockodo, then stores in the Secret Service                         |
| `Unlock() → s`                             | Asks the Secret Service to unlock (only on user request)                        |
| `GetSettings() → s` / `SetSettings(s) → s` | Settings including the list of languages                                        |
| Signal `StateChanged(s state)`             | Emitted only when the JSON actually changed                                     |

No member returns the API key or raw API responses, and there is no generic HTTP pass-through. `Start` and `Switch` accept only ids from lists the daemon loaded from Clockodo itself. Every process of the user session can call the interface; this is accepted on purpose, because such a process could read the Secret Service anyway.

Try it on a running system:

```bash
busctl --user call io.github.jmatthiesen81.ClockodoPlasma /io/github/jmatthiesen81/ClockodoPlasma \
    io.github.jmatthiesen81.ClockodoPlasma GetState
```

## State model

| `status`        | Meaning                                                                          |
| --------------- | -------------------------------------------------------------------------------- |
| `unknown`       | Credentials present, not synchronised yet                                        |
| `unconfigured`  | No credentials stored                                                            |
| `secret_locked` | Wallet locked, access denied or no Secret Service provider                       |
| `auth_failed`   | Clockodo answered 401 (e.g. key invalidated by a password change); polling stops |
| `running`       | A clock runs; `running` holds entry id, ids, label and start time                |
| `stopped`       | No clock runs                                                                    |

Additional fields: `today_seconds`, `computed_at`, `last_sync`, `syncing`, `action_pending` (buttons disabled), `stale`, `error`, `notice` + `notice_id` (one-time information), `timezone`, `timezone_mismatch`, `poll_interval`, `account`, `language`.

## Synchronisation and time

A sync reads `GET /v4/users/me` once (user id and Clockodo time zone), then `GET /v2/clock` and `GET /v2/workTimes` for today.

- **Coalescing:** concurrent callers share one running sync; triggers during a sync lead to one follow-up sync.
- **Schedule:** the configured interval; after errors an exponential back-off up to 15 minutes, at least `Retry-After` after a 429. Interval 0 switches scheduled polling off; the popup still triggers a sync.
- **Server time:** the running duration is based on Clockodo's `current_time` and advanced with the monotonic clock, so a wrong local clock does not matter.
- **Suspend:** `CLOCK_MONOTONIC` stops during suspend; a jump between wall clock and monotonic clock (≥ 5 s) triggers a sync, and after ≥ 2 minutes with a running clock a notification.
- **Today:** "today" is the calendar day in the user's Clockodo time zone. Day bounds are computed in UTC, so 23- and 25-hour days are correct. Intervals are clipped to the day, the running clock is merged in once, overlaps are merged. A day change triggers one sync.
- **Errors:** network errors and 5xx keep the last state and mark it `stale`; 401 sets `auth_failed` without retries.

## Booking safety

Implemented in [service.py](../../backend/clockodo_plasma/service.py) and covered by [test_service_actions.py](../../tests/unit/test_service_actions.py):

1. Write calls (start/stop) are **never retried** automatically.
2. Before a start the clock is **read fresh**. If a clock runs that the widget did not know, nothing is started and the running clock is shown. If Clockodo still reports a stopped entry, the message says so.
3. **Stop uses the entry id** the user saw. If another entry runs or the entry is gone (404/409), the state is reloaded and nothing is retried.
4. If the outcome of a write is **unknown** (timeout after sending, 5xx), the state is re-read and the result is reported; the buttons stay disabled until then.
5. **One action at a time** (lock in the daemon plus `action_pending`); a double click has no effect.
6. **No optimistic UI:** the widget changes only after Clockodo answered.
7. **Network errors never book.** A connection error before sending is reported as "nothing was booked".
8. Only **active** customers/projects/services loaded by the daemon are accepted; a project must belong to the customer. Subprojects are not supported yet.

**Switch** reads the clock first and sends a single `POST /v2/clock` only if exactly the shown entry still runs; Clockodo stops that entry itself. So there is no gap and no state "stopped, start failed".

## Clockodo API

Checked against the official OpenAPI specification (`https://docs.clockodo.com/openapi.yaml`, version 2026-11-17).

| Purpose             | Endpoint                                                                                                                                    |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Own user, time zone | `GET /v4/users/me`                                                                                                                          |
| Clock state         | `GET /v2/clock`                                                                                                                             |
| Start / switch      | `POST /v2/clock` with `customers_id`, `services_id`, optional `projects_id`, `text`                                                         |
| Stop                | `DELETE /v2/clock/{id}`                                                                                                                     |
| Today's work time   | `GET /v2/workTimes?date_since&date_until&users_id`                                                                                          |
| Selection lists     | `GET /v3/customers`, `GET /v4/projects`, `GET /v4/services` with `filter[active]=true` (projects also `filter[completed]=false`), paginated |

Every request sends `X-ClockodoApiUser`, `X-ClockodoApiKey` and `X-Clockodo-External-Application: clockodo-plasma;<contact e-mail>`. The contact defaults to the user's Clockodo e-mail. Base URL: `https://my.clockodo.com/api`. Rate limits per user: 900/min, 2,250/15 min, 4,500/h, 20,000/day.

Recently used contexts are not read from Clockodo; the daemon remembers its own starts and running entries it observed.

[Index](index.md) · [Deutsch](../de/architecture.md)
