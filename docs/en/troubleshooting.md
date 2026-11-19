# Troubleshooting

Known problems and what to do about them. The first look is always the log: `journalctl --user -u clockodo-plasma -e`.

## "Background service not reachable"

The widget cannot reach the daemon over D-Bus.

```bash
systemctl --user status clockodo-plasma
journalctl --user -u clockodo-plasma -e
ls /usr/share/dbus-1/services/io.github.jmatthiesen81.ClockodoPlasma.service
```

- After a package update the daemon may still run the old version: `systemctl --user restart clockodo-plasma`.
- If the unit is unknown, reload: `systemctl --user daemon-reload`.
- The unit restarts after crashes (`Restart=on-failure`); repeated crashes show up in the journal.

## Wallet locked

The popup says the wallet is locked (`secret_locked`). Press *Unlock* in the popup; KWallet asks for its password. The daemon never opens this prompt on its own. Do not enter the API key again; it is still stored.

## Secret Service not available

The message "No Secret Service available (KWallet)" means no program owns `org.freedesktop.secrets` on the session bus.

- Check: `busctl --user status org.freedesktop.secrets`.
- On some systems the Secret Service interface of KWallet must be switched on (`[org.freedesktop.secrets] apiEnabled=true` in `~/.config/kwalletrc`, according to the Arch Wiki; not verified on the target system).
- gnome-keyring can take the name instead of KWallet; then credentials are stored there.

## API key rejected

Status `auth_failed`: Clockodo answered 401. A password change in Clockodo invalidates the API key. Open the popup, enter the new key (Clockodo → *Personal data*). Polling stays off until then.

## Time is shown in italics / dimmed ("outdated")

The last sync failed or polling is off (`poll_interval = 0`). The popup shows the time of the last update and the error. Network errors and 5xx answers are retried with back-off (up to 15 minutes); press *Refresh* to try at once.

## "A clock is already running"

A clock was started on another device after the last sync. Nothing was booked. Stop it or use *Switch…*.

## "The answer from Clockodo was lost"

A start, stop or switch request was sent, but the answer did not arrive. The daemon re-read the state and reports what is true now. Check the result in the popup; nothing is retried automatically.

## Today's total differs from the Clockodo web app

"Today" is the calendar day in your Clockodo time zone. If it differs from the computer's time zone, the popup shows a hint. The total between syncs is advanced locally and corrected at the next sync.

## Widget changes are not visible after an update

Plasma keeps loaded QML. Restart `plasmashell` (`systemctl --user restart plasma-plasmashell`) or log out and in again.

[Index](index.md) · [Deutsch](../de/troubleshooting.md)
