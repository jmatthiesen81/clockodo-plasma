# Architektur

Wie Daemon und Widget aufgebaut sind, wie sie miteinander und mit Clockodo kommunizieren und welche Regeln vor Fehlbuchungen schützen.

## Designentscheidungen

| Entscheidung                                           | Grund                                                                                                                                                                                                                                             |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Widget plus Daemon statt reinem QML-Widget             | QML hat keine Secret-Service-API, der API-Key landete im Klartext in `plasma-org.kde.plasma.desktop-appletsrc`; `Plasmoid.configuration` gilt pro Widget-Instanz, jede Instanz würde also selbst pollen; Logik im Daemon ist ohne Plasma testbar. |
| Python-Daemon statt C++-Plugin                         | Ein C++-Plugin (z. B. mit qtkeychain) bindet das Paket an eine Architektur und erfordert bei jedem Qt-/KF-Update einen Neubau im eigenen Repository.                                                                                              |
| asyncio, httpx, dbus-fast, secretstorage statt PySide6 | Keine Qt-Laufzeit im Hintergrund; das Exportieren von Objekten mit PySide6/QtDBus ist umständlich. Alle Bibliotheken sind in Arch `extra`.                                                                                                        |
| Plasma ≥ 6.4                                           | `SignalWatcher` aus `org.kde.plasma.workspace.dbus` gibt es erst ab 6.4 (`asyncCall` ab 6.2). Ohne ihn müsste das Widget den Daemon abfragen.                                                                                                     |
| JSON-Strings über D-Bus                                | Triviale Übergabe zwischen Python und QML; kein Genauigkeitsverlust bei int64 in JavaScript.                                                                                                                                                      |
| `/v2/workTimes` für die Tagessumme                     | Clockodo führt Überlappungen zusammen und lässt Pauschalen weg; `/v2/entries` ist paginiert, enthält Pauschalen und eventuell Einträge anderer Nutzer.                                                                                            |
| Wechseln als ein `POST /v2/clock`                      | Clockodo stoppt den laufenden Eintrag selbst: keine Lücke, kein Zustand „gestoppt, Start fehlgeschlagen“.                                                                                                                                         |
| D-Bus-Aktivierung über die systemd-Unit                | Kein Autostart-Eintrag; `SystemdService=` ist nötig, weil Arch dbus-broker nutzt.                                                                                                                                                                 |
| Code in `/usr/lib/clockodo-plasma`                     | Ein Python-Minor-Update unter Arch (z. B. 3.13 → 3.14) bricht das Paket nicht, was bei `site-packages` passieren würde.                                                                                                                           |
| Eigener Übersetzungskatalog                            | Plasmas `i18n()` folgt immer der Systemsprache und lässt sich nicht pro Widget umschalten.                                                                                                                                                        |
| Zuletzt genutzte Kontexte lokal gemerkt                | Spart zusätzliche `/v2/entries`-Anfragen und schont das Rate-Limit; gespeichert werden nur IDs.                                                                                                                                                   |

## Komponenten

| Teil              | Ort                                                                                                                        | Technologie                                                                   |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Daemon            | [backend/clockodo_plasma/](../../backend/clockodo_plasma/)                                                                 | Python ≥ 3.12, asyncio, httpx, dbus-fast, secretstorage                       |
| Widget            | [plasmoid/](../../plasmoid/)                                                                                               | QML, Plasma 6 (`PlasmoidItem`), Kirigami, `org.kde.plasma.workspace.dbus`     |
| Startskript       | [packaging/clockodo-plasma-daemon](../../packaging/clockodo-plasma-daemon)                                                 | `/bin/sh`, führt `python3 -I` mit dem Code aus `/usr/lib/clockodo-plasma` aus |
| systemd-User-Unit | [packaging/clockodo-plasma.service](../../packaging/clockodo-plasma.service)                                               | `Type=dbus`, `Restart=on-failure`, kein `[Install]`                           |
| D-Bus-Aktivierung | [packaging/io.github.jmatthiesen81.ClockodoPlasma.service](../../packaging/io.github.jmatthiesen81.ClockodoPlasma.service) | `SystemdService=clockodo-plasma.service`                                      |

## Daemon-Module

| Modul                                                                  | Verantwortung                                                                                                                             |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| [main.py](../../backend/clockodo_plasma/main.py)                       | Einstiegspunkt: verbindet sich mit dem Session-Bus, initialisiert, belegt den Bus-Namen, läuft bis SIGTERM/Trennung                       |
| [api.py](../../backend/clockodo_plasma/api.py)                         | Clockodo-HTTP-Client, erforderliche Header, Fehlerabbildung, Datenklassen                                                                 |
| [service.py](../../backend/clockodo_plasma/service.py)                 | Orchestrierung: Synchronisierung, Starten/Stoppen/Wechseln mit den Sicherheitsregeln, Kontexte, Zugangsdaten, Einstellungen, Erinnerungen |
| [poller.py](../../backend/clockodo_plasma/poller.py)                   | Poll-Schleife (Intervall/Back-off, zusammengeführte Auslöser) und Ein-Sekunden-Takt                                                       |
| [state.py](../../backend/clockodo_plasma/state.py)                     | Veröffentlichter Zustand und seine JSON-Form                                                                                              |
| [time_calculator.py](../../backend/clockodo_plasma/time_calculator.py) | Tagesgrenzen (sommerzeitsicher, in UTC) und heutige Gesamtzeit aus Arbeitszeitintervallen                                                 |
| [clock.py](../../backend/clockodo_plasma/clock.py)                     | Am Server verankerte Zeit und Erkennung von Sprüngen der Systemuhr (Ruhezustand)                                                          |
| [dbus_interface.py](../../backend/clockodo_plasma/dbus_interface.py)   | Exportierte D-Bus-Schnittstelle                                                                                                           |
| [secret_store.py](../../backend/clockodo_plasma/secret_store.py)       | Secret-Service-Zugriff in einem Worker-Thread                                                                                             |
| [notifications.py](../../backend/clockodo_plasma/notifications.py)     | Desktop-Benachrichtigungen und Überwachung der Bildschirmsperre                                                                           |
| [config.py](../../backend/clockodo_plasma/config.py)                   | Einstellungen (TOML) und zuletzt verwendete Kontexte (JSON), Validierung, Schemaversion                                                   |
| [messages.py](../../backend/clockodo_plasma/messages.py)               | Texte des Daemons in allen Sprachen, Sprachauflösung                                                                                      |
| [logutil.py](../../backend/clockodo_plasma/logutil.py)                 | Logging nach stderr/journald mit Schwärzung registrierter Geheimnisse                                                                     |

## Widget-Dateien

| Datei                                                                             | Inhalt                                                                             |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| [metadata.json](../../plasmoid/metadata.json)                                     | Plugin-ID `io.github.jmatthiesen81.clockodoplasma`, Version, Lizenz                |
| [main.qml](../../plasmoid/contents/ui/main.qml)                                   | Zustand, D-Bus-Aufrufe, Signal- und Service-Watcher, Tooltip, `tr()`               |
| [CompactRepresentation.qml](../../plasmoid/contents/ui/CompactRepresentation.qml) | Kontrollleiste: Symbol, `HH:MM`, Warnsymbol                                        |
| [FullRepresentation.qml](../../plasmoid/contents/ui/FullRepresentation.qml)       | Popup mit Meldungen und den Ansichten Tracking/Zugangsdaten/gesperrt/Einstellungen |
| [ContextPicker.qml](../../plasmoid/contents/ui/ContextPicker.qml)                 | Zuletzt verwendete Kontexte und Auswahl von Kunde/Projekt/Leistung                 |
| [CredentialsForm.qml](../../plasmoid/contents/ui/CredentialsForm.qml)             | E-Mail und API-Schlüssel                                                           |
| [SettingsView.qml](../../plasmoid/contents/ui/SettingsView.qml)                   | Sprache, Intervall, Erinnerungen, Kontakt-E-Mail                                   |
| [translations.js](../../plasmoid/contents/ui/translations.js)                     | Widget-Übersetzungen, geordnet nach dem englischen Text                            |

Das Widget hält eine lokale Kopie des Zustands und schreibt die Gesamtzeit alle 10 Sekunden fort, solange die Uhr läuft; der Daemon korrigiert sie jede Minute. Trifft kein Signal ein, liest das Widget den Zustand alle 2 Minuten neu.

## D-Bus-Schnittstelle

Bus-Name, Schnittstelle: `io.github.jmatthiesen81.ClockodoPlasma`; Objektpfad: `/io/github/jmatthiesen81/ClockodoPlasma`. Alle Argumente und Ergebnisse sind Strings; strukturierte Daten sind JSON. Das hält das Marshalling zwischen Python und QML trivial und vermeidet Genauigkeitsverlust bei int64 in JavaScript (Eintrags-IDs werden als Strings übergeben).

| Mitglied                                   | Ergebnis / Zweck                                                                |
| ------------------------------------------ | ------------------------------------------------------------------------------- |
| `GetState() → s`                           | Aktueller Zustand als JSON (siehe unten)                                        |
| `Refresh()`                                | Fordert eine sofortige Synchronisierung an                                      |
| `ListContexts() → s`                       | Aktive Kunden, Projekte, Leistungen und die zuletzt verwendeten Kontexte        |
| `Start(s context) → s`                     | `{"ok", "message"}`; Kontext `{customers_id, projects_id?, services_id, text?}` |
| `Stop(s entry_id) → s`                     | Stoppt genau diesen Eintrag                                                     |
| `Switch(s context, s entry_id) → s`        | Ersetzt den laufenden Eintrag `entry_id` durch einen neuen Kontext              |
| `SetCredentials(s email, s api_key) → s`   | Prüft bei Clockodo, speichert dann im Secret Service                            |
| `Unlock() → s`                             | Bittet den Secret Service um Entsperrung (nur auf Benutzeranfrage)              |
| `GetSettings() → s` / `SetSettings(s) → s` | Einstellungen einschließlich der Sprachliste                                    |
| Signal `StateChanged(s state)`             | Wird nur gesendet, wenn sich das JSON tatsächlich geändert hat                  |

Kein Mitglied gibt den API-Schlüssel oder rohe API-Antworten zurück, und es gibt keinen generischen HTTP-Durchgriff. `Start` und `Switch` akzeptieren nur IDs aus Listen, die der Daemon selbst von Clockodo geladen hat. Jeder Prozess der Benutzersitzung kann die Schnittstelle aufrufen; das wird bewusst akzeptiert, weil ein solcher Prozess ohnehin den Secret Service lesen könnte.

Auf einem laufenden System ausprobieren:

```bash
busctl --user call io.github.jmatthiesen81.ClockodoPlasma /io/github/jmatthiesen81/ClockodoPlasma \
    io.github.jmatthiesen81.ClockodoPlasma GetState
```

## Zustandsmodell

| `status`        | Bedeutung                                                                                              |
| --------------- | ------------------------------------------------------------------------------------------------------ |
| `unknown`       | Zugangsdaten vorhanden, noch nicht synchronisiert                                                      |
| `unconfigured`  | Keine Zugangsdaten gespeichert                                                                         |
| `secret_locked` | Brieftasche gesperrt, Zugriff verweigert oder kein Secret-Service-Anbieter                             |
| `auth_failed`   | Clockodo hat mit 401 geantwortet (z. B. Schlüssel durch Passwortänderung ungültig); das Polling stoppt |
| `running`       | Eine Uhr läuft; `running` enthält Eintrags-ID, IDs, Bezeichnung und Startzeit                          |
| `stopped`       | Keine Uhr läuft                                                                                        |

Weitere Felder: `today_seconds`, `computed_at`, `last_sync`, `syncing`, `action_pending` (Schaltflächen deaktiviert), `stale`, `error`, `notice` + `notice_id` (einmalige Information), `timezone`, `timezone_mismatch`, `poll_interval`, `account`, `language`.

## Synchronisierung und Zeit

Eine Synchronisierung liest einmal `GET /v4/users/me` (Benutzer-ID und Clockodo-Zeitzone), dann `GET /v2/clock` und `GET /v2/workTimes` für heute.

- **Zusammenfassen:** Gleichzeitige Aufrufer teilen sich eine laufende Synchronisierung; Auslöser während einer Synchronisierung führen zu einer Folgesynchronisierung.
- **Zeitplan:** das konfigurierte Intervall; nach Fehlern ein exponentieller Back-off bis zu 15 Minuten, nach einem 429 mindestens `Retry-After`. Intervall 0 schaltet das geplante Polling aus; das Popup löst weiterhin eine Synchronisierung aus.
- **Serverzeit:** Die laufende Dauer beruht auf dem `current_time` von Clockodo und wird mit der monotonen Uhr fortgeschrieben, eine falsche lokale Uhr spielt also keine Rolle.
- **Ruhezustand:** `CLOCK_MONOTONIC` steht im Ruhezustand still; ein Sprung zwischen Systemuhr und monotoner Uhr (≥ 5 s) löst eine Synchronisierung aus, und nach ≥ 2 Minuten bei laufender Uhr eine Benachrichtigung.
- **Heute:** „Heute“ ist der Kalendertag in der Clockodo-Zeitzone des Benutzers. Die Tagesgrenzen werden in UTC berechnet, sodass 23- und 25-Stunden-Tage korrekt sind. Intervalle werden auf den Tag beschnitten, die laufende Uhr wird einmal einbezogen, Überlappungen werden zusammengeführt. Ein Tageswechsel löst eine Synchronisierung aus.
- **Fehler:** Netzwerkfehler und 5xx behalten den letzten Zustand und markieren ihn als `stale`; 401 setzt `auth_failed` ohne Wiederholungen.

## Buchungssicherheit

Umgesetzt in [service.py](../../backend/clockodo_plasma/service.py) und abgedeckt durch [test_service_actions.py](../../tests/unit/test_service_actions.py):

1. Schreibaufrufe (Starten/Stoppen) werden **nie automatisch wiederholt**.
2. Vor einem Start wird die Uhr **frisch gelesen**. Läuft eine Uhr, die das Widget nicht kannte, wird nichts gestartet und die laufende Uhr angezeigt. Meldet Clockodo noch einen gestoppten Eintrag, sagt die Meldung das.
3. **Stopp verwendet die Eintrags-ID**, die der Benutzer gesehen hat. Läuft ein anderer Eintrag oder existiert der Eintrag nicht mehr (404/409), wird der Zustand neu geladen und nichts wiederholt.
4. Ist das Ergebnis eines Schreibaufrufs **unbekannt** (Timeout nach dem Senden, 5xx), wird der Zustand neu gelesen und das Ergebnis gemeldet; die Schaltflächen bleiben bis dahin deaktiviert.
5. **Immer nur eine Aktion** (Sperre im Daemon plus `action_pending`); ein Doppelklick bleibt wirkungslos.
6. **Keine optimistische Oberfläche:** Das Widget ändert sich erst, nachdem Clockodo geantwortet hat.
7. **Netzwerkfehler buchen nie.** Ein Verbindungsfehler vor dem Senden wird als „es wurde nichts gebucht“ gemeldet.
8. Nur **aktive** Kunden/Projekte/Leistungen, die der Daemon geladen hat, werden akzeptiert; ein Projekt muss zum Kunden gehören. Unterprojekte werden noch nicht unterstützt.

**Wechseln** liest zuerst die Uhr und sendet nur dann ein einzelnes `POST /v2/clock`, wenn genau der angezeigte Eintrag noch läuft; Clockodo stoppt diesen Eintrag selbst. Es gibt also keine Lücke und keinen Zustand „gestoppt, Start fehlgeschlagen“.

## Clockodo-API

Geprüft gegen die offizielle OpenAPI-Spezifikation (`https://docs.clockodo.com/openapi.yaml`, Version 2026-11-17).

| Zweck                      | Endpunkt                                                                                                                                         |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Eigener Benutzer, Zeitzone | `GET /v4/users/me`                                                                                                                               |
| Uhrzustand                 | `GET /v2/clock`                                                                                                                                  |
| Starten / Wechseln         | `POST /v2/clock` mit `customers_id`, `services_id`, optional `projects_id`, `text`                                                               |
| Stoppen                    | `DELETE /v2/clock/{id}`                                                                                                                          |
| Heutige Arbeitszeit        | `GET /v2/workTimes?date_since&date_until&users_id`                                                                                               |
| Auswahllisten              | `GET /v3/customers`, `GET /v4/projects`, `GET /v4/services` mit `filter[active]=true` (Projekte zusätzlich `filter[completed]=false`), paginiert |

Jede Anfrage sendet `X-ClockodoApiUser`, `X-ClockodoApiKey` und `X-Clockodo-External-Application: clockodo-plasma;<Kontakt-E-Mail>`. Der Kontakt ist standardmäßig die Clockodo-E-Mail des Benutzers. Basis-URL: `https://my.clockodo.com/api`. Ratenlimits pro Benutzer: 900/min, 2.250/15 min, 4.500/h, 20.000/Tag.

Zuletzt verwendete Kontexte werden nicht aus Clockodo gelesen; der Daemon merkt sich seine eigenen Starts und beobachtete laufende Einträge.

[Index](index.md) · [English](../en/architecture.md)
