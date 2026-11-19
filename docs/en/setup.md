# Setup

Requirements, installation, first start and removal of Clockodo Plasma.

## Requirements

| Item           | Requirement                                                                                                                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System         | CachyOS or Arch Linux                                                                                                                                         |
| Desktop        | KDE Plasma ≥ 6.4 (the widget needs the D-Bus `SignalWatcher` of `plasma-workspace` 6.4)                                                                       |
| Secret Service | KWallet (`ksecretd`) or another provider of `org.freedesktop.secrets`                                                                                         |
| Clockodo       | Account with an API key (Clockodo → *Personal data*)                                                                                                          |
| Package deps   | `python`, `python-httpx`, `python-dbus-fast`, `python-secretstorage`, `plasma-workspace>=6.4`, `libplasma`, `kirigami`, `qt6-declarative`; optional `kwallet` |

All dependencies are in Arch `extra`.

## Installation

### From the pacman repository

Once the own pacman repository is configured in `/etc/pacman.conf` and the package is published:

```bash
sudo pacman -Syu clockodo-plasma
```

### From a local build

Needs Docker (or Podman with `CONTAINER_RUNTIME=podman`):

```bash
scripts/build-package.sh --check
sudo pacman -U dist/clockodo-plasma-*-any.pkg.tar.zst
```

### Installed files

| Path                                                                                      | Content                              |
| ----------------------------------------------------------------------------------------- | ------------------------------------ |
| `/usr/bin/clockodo-plasma-daemon`                                                         | Start script                         |
| `/usr/lib/clockodo-plasma/clockodo_plasma/`                                               | Python code (not in `site-packages`) |
| `/usr/lib/systemd/user/clockodo-plasma.service`                                           | systemd user unit                    |
| `/usr/share/dbus-1/services/io.github.jmatthiesen81.ClockodoPlasma.service`               | D-Bus activation                     |
| `/usr/share/plasma/plasmoids/io.github.jmatthiesen81.clockodoplasma/`                     | Widget                               |
| `/usr/share/doc/clockodo-plasma/README.md`, `/usr/share/licenses/clockodo-plasma/LICENSE` | Documentation, license               |

## First start

1. Right-click the panel → *Add Widgets…* → *Clockodo Time Tracking* (German: *Clockodo-Zeiterfassung*).
2. Click the widget. The daemon starts automatically through D-Bus activation.
3. Enter the Clockodo e-mail and API key and press *Check and save*. The daemon checks them with Clockodo and stores them in KWallet. The key grants the same access as your password.
4. Choose customer, optionally project, and service, then *Start*.
5. Optional: open the settings (gear icon) for language, interval, reminders and contact e-mail.

If the popup shows "wallet locked", press *Unlock*. If the Secret Service is not available at all, see [Troubleshooting](troubleshooting.md#secret-service-not-available).

## Update

```bash
sudo pacman -Syu
systemctl --user restart clockodo-plasma   # or log out and in again
```

A running daemon keeps the old version until it restarts; a changed widget is loaded after restarting `plasmashell` or a new login. The package prints this hint after an upgrade.

## Uninstall

```bash
sudo pacman -Rns clockodo-plasma
```

Personal data stays on purpose. To remove it as well:

```bash
rm -r ~/.config/clockodo-plasma ~/.local/state/clockodo-plasma
secret-tool clear application clockodo-plasma   # or delete the entry in KWalletManager
```

Remove the widget from the panel too; otherwise it stays as a broken widget.

[Index](index.md) · [Deutsch](../de/setup.md)
