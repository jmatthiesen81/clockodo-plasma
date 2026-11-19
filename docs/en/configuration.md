# Configuration

All settings and stored data, where they live and what they control. Settings are global for the daemon and shared by all widget instances; they are edited in the popup (gear icon), not in the Plasma configuration dialog.

## Settings file

`~/.config/clockodo-plasma/config.toml` (respects `XDG_CONFIG_HOME`), written by the daemon ([config.py](../../backend/clockodo_plasma/config.py)):

| Key                  | Default    | Values                        | Effect                                                                |
| -------------------- | ---------- | ----------------------------- | --------------------------------------------------------------------- |
| `schema_version`     | `1`        | integer                       | Version of the file format, for migrations                            |
| `poll_interval`      | `60`       | `0`, `30`, `60`, `120`, `300` | Seconds between syncs; `0` = no scheduled polling                     |
| `contact_email`      | `""`       | e-mail or empty               | Contact in `X-Clockodo-External-Application`; empty = Clockodo e-mail |
| `notify_on_lock`     | `true`     | boolean                       | Notification when the screen is locked while the clock runs           |
| `long_running_hours` | `0`        | `0`–`24`                      | Notification once per entry after this many hours; `0` = off          |
| `language`           | `"system"` | `system`, `en`, `de`          | Language of widget, messages and notifications                        |

Unknown keys are ignored. A file that cannot be read or contains invalid values falls back to the defaults (with a warning in the log).

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
