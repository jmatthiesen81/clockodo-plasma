# Configuration

All settings and stored data, where they live and what they control. Settings are global for the daemon and shared by all widget instances; they are edited in the widget's configuration dialog and stored by the daemon.

## Settings file

`~/.config/clockodo-plasma/config.toml` (respects `XDG_CONFIG_HOME`), written by the daemon ([config.py](../../backend/clockodo_plasma/config.py)):

| Key                       | Default    | Values                         | Effect                                                                             |
| ------------------------- | ---------- | ------------------------------ | ---------------------------------------------------------------------------------- |
| `schema_version`          | `1`        | integer                        | Version of the file format, for migrations                                         |
| `poll_interval`           | `60`       | `0`, `30`, `60`, `120`, `300`  | Seconds between syncs; `0` = no scheduled polling                                  |
| `contact_email`           | `""`       | e-mail or empty                | Contact in `X-Clockodo-External-Application`; empty = Clockodo e-mail              |
| `notify_on_lock`          | `true`     | boolean                        | Notification when the screen is locked while the clock runs                        |
| `long_running_hours`      | `0`        | `0`–`24`                       | Notification once per entry after this many hours; `0` = off                       |
| `language`                | `"system"` | `system`, `en`, `de`           | Language of widget, messages and notifications                                     |
| `default_customers_id`    | `0`        | customer id, `0` = none        | Default booking for the quick start (needs a service)                              |
| `default_projects_id`     | `0`        | project id, `0` = none         | Project of the default booking                                                     |
| `default_services_id`     | `0`        | service id, `0` = none         | Service of the default booking (needs a customer)                                  |
| `default_text`            | `""`       | up to 1000 characters          | Description of the default booking                                                 |
| `panel_style`             | `"ring"`   | `ring`, `stopwatch`, `pill`    | Panel display: progress ring, stopwatch, or coloured time only                     |
| `colorize`                | `true`     | boolean                        | Time in the panel green while running, orange while stopped                        |
| `modifier`                | `"ctrl"`   | `ctrl`, `shift`, `alt`, `meta` | Key for key + left click                                                           |
| `modifier_click`          | `"quick"`  | `quick`, `picker`, `none`      | Key + left click: quick start/stop, open start with selection, nothing             |
| `middle_click`            | `"quick"`  | `quick`, `picker`, `none`      | Middle click, same choices                                                         |
| `overtime_color`          | `true`     | boolean                        | Red when today's total exceeds the daily target                                    |
| `overtime_notify`         | `true`     | boolean                        | Notification with a *Stop* button when the target is exceeded while the clock runs |
| `overtime_after_minutes`  | `0`        | `0`–`240`                      | Minutes over target before the first warning                                       |
| `overtime_repeat_minutes` | `60`       | `0`–`480`                      | Minutes between warnings; `0` = once per day                                       |

Unknown keys are ignored. A file that cannot be read or contains invalid values falls back to the defaults (with a warning in the log).

## Configuration dialog

Right-click the widget → *Configure Clockodo Time Tracking…*, or the gear icon in the popup. The pages read the settings from the daemon and save them with *Apply*/*OK*:

| Page            | Settings                                                                        |
| --------------- | ------------------------------------------------------------------------------- |
| Default booking | Customer, project, service and description for the quick start                  |
| Controls        | Panel style, colours, key + left click, middle click                            |
| Reminders       | Daily target (red, warning, tolerance, repeat), screen lock, long-running clock |
| General         | Language, update interval, contact e-mail                                       |
| Account         | Clockodo e-mail and API key (saved with their own button after a check)         |

## Quick start and daily target

- **Quick start/stop** (key + left click, middle click, context menu): starts the default booking or stops the clock the panel shows. The usual safety rules apply: a clock running elsewhere is never replaced, and only the shown entry is stopped. Without a default booking the selection opens. Failures are shown as a notification, because the popup is usually closed.
- **Daily target:** read once per day from Clockodo's day report (`GET /userreports/{id}?type=3`), which already accounts for public holidays, absences and changed target hours. Without target hours, or without permission to read the report, there is no ring progress, no red and no warning.

## Language

`system` uses the first supported language from `LANGUAGE` (a colon-separated list), `LC_ALL`, `LC_MESSAGES`, `LANG`, in this order; if none is supported, English. The daemon resolves the language and publishes it in the state, so the widget, the daemon's messages and the notifications always use the same language. Until the daemon answers, the widget uses the Qt locale. The widget name in the widget list follows the system language, because Plasma shows it from `metadata.json`.

## Stored data

| Data                   | Location                                                                                                                      | Notes                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| Recently used contexts | `~/.local/state/clockodo-plasma/state.json` (`XDG_STATE_HOME`)                                                                | Up to 5, ids only, no names or texts |
| E-mail and API key     | Secret Service item, label "Clockodo API key (clockodo-plasma)", attributes `application=clockodo-plasma`, `account=<e-mail>` | Never written to files or logs       |

Both files are written atomically (temporary file, then rename).

## Environment variables

| Variable                                    | Used by                    | Effect                                                             |
| ------------------------------------------- | -------------------------- | ------------------------------------------------------------------ |
| `XDG_CONFIG_HOME`, `XDG_STATE_HOME`         | daemon                     | Base directories for settings and state                            |
| `LANGUAGE`, `LC_ALL`, `LC_MESSAGES`, `LANG` | daemon                     | System language for `language = "system"`                          |
| `DBUS_SESSION_BUS_ADDRESS`                  | daemon, D-Bus tests        | Session bus; D-Bus tests are skipped without it                    |
| `CONTAINER_RUNTIME`                         | `scripts/build-package.sh` | `docker` (default) or `podman`                                     |
| `CLOCKODO_IMAGE`                            | `scripts/build-package.sh` | Tag of the Arch image (default `clockodo-plasma-arch:latest`)      |
| `CLOCKODO_TEST_SYSTEM`                      | `scripts/test.sh`          | `1` = use the system Python instead of `.venv`                     |
| `CLOCKODO_PLASMA_SRC`                       | `packaging/arch/PKGBUILD`  | Source tree for the build (default: two levels above the PKGBUILD) |

The start script runs Python with `-I`, so `PYTHONPATH` and the user's site-packages have no effect on the daemon.

## systemd and D-Bus

[clockodo-plasma.service](../../packaging/clockodo-plasma.service):

| Setting                                                                      | Why                                                       |
| ---------------------------------------------------------------------------- | --------------------------------------------------------- |
| `Type=dbus`, `BusName=io.github.jmatthiesen81.ClockodoPlasma`                | systemd knows the service is ready when the name is taken |
| `Restart=on-failure`, `RestartSec=5`                                         | Restart after a crash                                     |
| `PartOf=` / `After=graphical-session.target`                                 | Stops with the graphical session                          |
| `NoNewPrivileges`, `LockPersonality`, `RestrictRealtime`, `RestrictSUIDSGID` | Basic hardening                                           |
| no `[Install]` section                                                       | Started on demand only, via D-Bus activation              |

The D-Bus service file names `SystemdService=clockodo-plasma.service`. This is needed on Arch, where dbus-broker activates services only through systemd.

[Index](index.md) · [Deutsch](../de/configuration.md)
