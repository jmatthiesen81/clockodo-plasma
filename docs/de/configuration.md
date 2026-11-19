# Konfiguration

Alle Einstellungen und gespeicherten Daten, wo sie liegen und was sie steuern. Die Einstellungen gelten global für den Daemon und werden von allen Widget-Instanzen gemeinsam genutzt; sie werden im Konfigurationsdialog des Widgets bearbeitet und vom Daemon gespeichert.

## Einstellungsdatei

`~/.config/clockodo-plasma/config.toml` (beachtet `XDG_CONFIG_HOME`), vom Daemon geschrieben ([config.py](../../backend/clockodo_plasma/config.py)):

| Schlüssel                 | Standard   | Werte                          | Wirkung                                                                                 |
| ------------------------- | ---------- | ------------------------------ | --------------------------------------------------------------------------------------- |
| `schema_version`          | `1`        | Ganzzahl                       | Version des Dateiformats, für Migrationen                                               |
| `poll_interval`           | `60`       | `0`, `30`, `60`, `120`, `300`  | Sekunden zwischen Synchronisierungen; `0` = kein geplantes Polling                      |
| `contact_email`           | `""`       | E-Mail oder leer               | Kontakt in `X-Clockodo-External-Application`; leer = Clockodo-E-Mail                    |
| `notify_on_lock`          | `true`     | Boolean                        | Benachrichtigung, wenn der Bildschirm gesperrt wird, während die Uhr läuft              |
| `long_running_hours`      | `0`        | `0`–`24`                       | Einmalige Benachrichtigung pro Eintrag nach dieser Anzahl Stunden; `0` = aus            |
| `language`                | `"system"` | `system`, `en`, `de`           | Sprache von Widget, Meldungen und Benachrichtigungen                                    |
| `default_customers_id`    | `0`        | Kunden-ID, `0` = keine         | Standardbuchung für den Schnellstart (braucht eine Leistung)                            |
| `default_projects_id`     | `0`        | Projekt-ID, `0` = keines       | Projekt der Standardbuchung                                                             |
| `default_services_id`     | `0`        | Leistungs-ID, `0` = keine      | Leistung der Standardbuchung (braucht einen Kunden)                                     |
| `default_text`            | `""`       | bis 1000 Zeichen               | Beschreibung der Standardbuchung                                                        |
| `panel_style`             | `"ring"`   | `ring`, `stopwatch`, `pill`    | Anzeige in der Leiste: Fortschrittsring, Stoppuhr oder nur farbige Zeit                 |
| `colorize`                | `true`     | Boolean                        | Zeit in der Leiste grün bei laufender, orange bei gestoppter Uhr                        |
| `modifier`                | `"ctrl"`   | `ctrl`, `shift`, `alt`, `meta` | Taste für Taste + Linksklick                                                            |
| `modifier_click`          | `"quick"`  | `quick`, `picker`, `none`      | Taste + Linksklick: Schnellstart/-stopp, Start mit Auswahl öffnen, nichts               |
| `middle_click`            | `"quick"`  | `quick`, `picker`, `none`      | Mittelklick, gleiche Auswahl                                                            |
| `overtime_color`          | `true`     | Boolean                        | Rot, wenn die heutige Zeit das Tagessoll überschreitet                                  |
| `overtime_notify`         | `true`     | Boolean                        | Benachrichtigung mit *Stoppen*-Knopf, wenn das Soll bei laufender Uhr überschritten ist |
| `overtime_after_minutes`  | `0`        | `0`–`240`                      | Minuten über Soll bis zur ersten Warnung                                                |
| `overtime_repeat_minutes` | `60`       | `0`–`480`                      | Minuten zwischen den Warnungen; `0` = einmal pro Tag                                    |

Unbekannte Schlüssel werden ignoriert. Eine Datei, die nicht gelesen werden kann oder ungültige Werte enthält, führt zu den Standardwerten (mit einer Warnung im Log).

## Konfigurationsdialog

Rechtsklick auf das Widget → *Clockodo-Zeiterfassung einrichten …*, oder das Zahnradsymbol im Popup. Die Seiten lesen die Einstellungen vom Daemon und speichern sie mit *Anwenden*/*OK*:

| Seite           | Einstellungen                                                                          |
| --------------- | -------------------------------------------------------------------------------------- |
| Standardbuchung | Kunde, Projekt, Leistung und Beschreibung für den Schnellstart                         |
| Bedienung       | Stil in der Leiste, Farben, Taste + Linksklick, Mittelklick                            |
| Erinnerungen    | Tagessoll (rot, Warnung, Toleranz, Wiederholung), Bildschirmsperre, lange laufende Uhr |
| Allgemein       | Sprache, Aktualisierungsintervall, Kontakt-E-Mail                                      |
| Konto           | Clockodo-E-Mail und API-Schlüssel (nach Prüfung mit eigenem Knopf gespeichert)         |

## Schnellstart und Tagessoll

- **Schnellstart/-stopp** (Taste + Linksklick, Mittelklick, Kontextmenü): startet die Standardbuchung oder stoppt die Uhr, die die Leiste anzeigt. Es gelten die üblichen Sicherheitsregeln: Eine anderswo laufende Uhr wird nie ersetzt, und gestoppt wird nur der angezeigte Eintrag. Ohne Standardbuchung öffnet sich die Auswahl. Fehler erscheinen als Benachrichtigung, weil das Popup meist geschlossen ist.
- **Tagessoll:** einmal pro Tag aus dem Tagesbericht von Clockodo gelesen (`GET /userreports/{id}?type=3`); Feiertage, Abwesenheiten und geänderte Sollstunden sind dort schon berücksichtigt. Ohne Sollstunden oder ohne Recht, den Bericht zu lesen, gibt es keinen Ringfortschritt, kein Rot und keine Warnung.

## Sprache

`system` verwendet die erste unterstützte Sprache aus `LANGUAGE` (eine durch Doppelpunkte getrennte Liste), `LC_ALL`, `LC_MESSAGES`, `LANG`, in dieser Reihenfolge; ist keine unterstützt, Englisch. Der Daemon ermittelt die Sprache und veröffentlicht sie im Zustand, sodass Widget, Meldungen des Daemons und Benachrichtigungen stets dieselbe Sprache nutzen. Bis der Daemon antwortet, verwendet das Widget die Qt-Locale. Der Widget-Name in der Widget-Liste folgt der Systemsprache, weil Plasma ihn aus `metadata.json` anzeigt.

## Gespeicherte Daten

| Daten                       | Ort                                                                                                                                   | Hinweise                                    |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| Zuletzt verwendete Kontexte | `~/.local/state/clockodo-plasma/state.json` (`XDG_STATE_HOME`)                                                                        | Bis zu 5, nur IDs, keine Namen oder Texte   |
| E-Mail und API-Schlüssel    | Secret-Service-Eintrag, Bezeichnung „Clockodo API key (clockodo-plasma)“, Attribute `application=clockodo-plasma`, `account=<E-Mail>` | Werden nie in Dateien oder Logs geschrieben |

Beide Dateien werden atomar geschrieben (temporäre Datei, dann Umbenennen).

## Umgebungsvariablen

| Variable                                    | Verwendet von              | Wirkung                                                           |
| ------------------------------------------- | -------------------------- | ----------------------------------------------------------------- |
| `XDG_CONFIG_HOME`, `XDG_STATE_HOME`         | Daemon                     | Basisverzeichnisse für Einstellungen und Zustand                  |
| `LANGUAGE`, `LC_ALL`, `LC_MESSAGES`, `LANG` | Daemon                     | Systemsprache für `language = "system"`                           |
| `DBUS_SESSION_BUS_ADDRESS`                  | Daemon, D-Bus-Tests        | Session-Bus; D-Bus-Tests werden ohne ihn übersprungen             |
| `CONTAINER_RUNTIME`                         | `scripts/build-package.sh` | `docker` (Standard) oder `podman`                                 |
| `CLOCKODO_IMAGE`                            | `scripts/build-package.sh` | Tag des Arch-Images (Standard `clockodo-plasma-arch:latest`)      |
| `CLOCKODO_TEST_SYSTEM`                      | `scripts/test.sh`          | `1` = System-Python statt `.venv` verwenden                       |
| `CLOCKODO_PLASMA_SRC`                       | `packaging/arch/PKGBUILD`  | Quellbaum für den Build (Standard: zwei Ebenen über dem PKGBUILD) |

Das Startskript führt Python mit `-I` aus, daher haben `PYTHONPATH` und die Site-Packages des Benutzers keine Wirkung auf den Daemon.

## systemd und D-Bus

[clockodo-plasma.service](../../packaging/clockodo-plasma.service):

| Einstellung                                                                  | Warum                                                                |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `Type=dbus`, `BusName=io.github.jmatthiesen81.ClockodoPlasma`                | systemd weiß, dass der Dienst bereit ist, sobald der Name belegt ist |
| `Restart=on-failure`, `RestartSec=5`                                         | Neustart nach einem Absturz                                          |
| `PartOf=` / `After=graphical-session.target`                                 | Endet mit der grafischen Sitzung                                     |
| `NoNewPrivileges`, `LockPersonality`, `RestrictRealtime`, `RestrictSUIDSGID` | Grundlegende Härtung                                                 |
| kein `[Install]`-Abschnitt                                                   | Wird nur bei Bedarf über die D-Bus-Aktivierung gestartet             |

Die D-Bus-Service-Datei nennt `SystemdService=clockodo-plasma.service`. Das ist unter Arch nötig, wo dbus-broker Dienste ausschließlich über systemd aktiviert.

[Index](index.md) · [English](../en/configuration.md)
