# Fehlerbehebung

Bekannte Probleme und was dagegen zu tun ist. Der erste Blick gilt immer dem Log: `journalctl --user -u clockodo-plasma -e`.

## „Hintergrunddienst nicht erreichbar“

Das Widget erreicht den Daemon nicht über D-Bus.

```bash
systemctl --user status clockodo-plasma
journalctl --user -u clockodo-plasma -e
ls /usr/share/dbus-1/services/io.github.jmatthiesen81.ClockodoPlasma.service
```

- Nach einem Paket-Update läuft der Daemon unter Umständen noch in der alten Version: `systemctl --user restart clockodo-plasma`.
- Ist die Unit unbekannt, neu laden: `systemctl --user daemon-reload`.
- Die Unit startet nach Abstürzen neu (`Restart=on-failure`); wiederholte Abstürze erscheinen im Journal.

## Brieftasche gesperrt

Das Popup meldet, dass die Brieftasche gesperrt ist (`secret_locked`). Im Popup *Entsperren* drücken; KWallet fragt nach seinem Passwort. Der Daemon öffnet diese Abfrage nie von selbst. Den API-Schlüssel nicht erneut eingeben; er ist weiterhin gespeichert.

## Secret Service nicht verfügbar

Die Meldung „Kein Secret Service verfügbar (KWallet)“ bedeutet, dass kein Programm `org.freedesktop.secrets` auf dem Session-Bus besitzt.

- Prüfen: `busctl --user status org.freedesktop.secrets`.
- Auf manchen Systemen muss die Secret-Service-Schnittstelle von KWallet eingeschaltet werden (`[org.freedesktop.secrets] apiEnabled=true` in `~/.config/kwalletrc`, laut Arch Wiki; auf dem Zielsystem nicht verifiziert).
- gnome-keyring kann den Namen anstelle von KWallet übernehmen; die Zugangsdaten werden dann dort gespeichert.

## API-Schlüssel abgelehnt

Status `auth_failed`: Clockodo hat mit 401 geantwortet. Eine Passwortänderung in Clockodo macht den API-Schlüssel ungültig. Das Popup öffnen und den neuen Schlüssel eingeben (Clockodo → *Persönliche Daten*). Bis dahin bleibt das Polling aus.

## Zeit wird kursiv / abgeblendet angezeigt („veraltet“)

Die letzte Synchronisierung ist fehlgeschlagen oder das Polling ist aus (`poll_interval = 0`). Das Popup zeigt den Zeitpunkt der letzten Aktualisierung und den Fehler. Netzwerkfehler und 5xx-Antworten werden mit Back-off (bis zu 15 Minuten) wiederholt; *Aktualisieren* drücken, um sofort einen Versuch zu starten.

## „Es läuft bereits eine Uhr“

Nach der letzten Synchronisierung wurde auf einem anderen Gerät eine Uhr gestartet. Es wurde nichts gebucht. Sie stoppen oder *Wechseln …* verwenden.

## „Die Antwort von Clockodo ging verloren“

Eine Start-, Stopp- oder Wechsel-Anfrage wurde gesendet, die Antwort ist aber nicht angekommen. Der Daemon hat den Zustand neu gelesen und meldet, was jetzt gilt. Das Ergebnis im Popup prüfen; es wird nichts automatisch wiederholt.

## Die heutige Gesamtzeit weicht von der Clockodo-Web-App ab

„Heute“ ist der Kalendertag in der Clockodo-Zeitzone. Weicht sie von der Zeitzone des Rechners ab, zeigt das Popup einen Hinweis. Die Gesamtzeit zwischen Synchronisierungen wird lokal fortgeschrieben und bei der nächsten Synchronisierung korrigiert.

## Widget-Änderungen sind nach einem Update nicht sichtbar

Plasma behält geladenes QML. `plasmashell` neu starten (`systemctl --user restart plasma-plasmashell`) oder ab- und wieder anmelden.

[Index](index.md) · [English](../en/troubleshooting.md)
