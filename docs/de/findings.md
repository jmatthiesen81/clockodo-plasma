# Befunde

Risiken, ungetestete Bereiche und offene Punkte für Version 0.2.0 (2026-11-19).

## Noch nicht getestet

| Bereich                                              | Status                                                                                                                                                                                                                                                                                                                                    |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Widget in einer echten Plasma-Sitzung                | 0.1.1 lief unter CachyOS: Popup, Zugangsdaten-Formular und Einstellungen funktionieren. Die Funktionen von 0.2.0 (Stile in der Leiste, Schnellstart/-stopp, Kontextmenü, Konfigurationsdialog, Soll-Warnung mit *Stoppen*-Knopf) liefen nur in `plasmoidviewer` im Arch-Container gegen den Daemon mit einem Clockodo-Client im Speicher. |
| Echtes Clockodo-Konto                                | 0.1.1 hat ein echtes Konto gelesen (Benutzer, Tagessumme, Kunden, Projekte, Leistungen). Starten, Stoppen und Wechseln sind gegen ein echtes Konto bestätigt (2026-11-23). Der Tagesbericht für das Tagessoll wurde gegen ein echtes Konto geprüft, die Anfrage des Widgets selbst nur gegen Mocks.                                       |
| KWallet / Secret Service                             | Speichern und Lesen der Zugangsdaten funktioniert mit KWallet unter CachyOS; gesperrte Brieftasche und „kein Anbieter“ sind nur durch Tests abgedeckt.                                                                                                                                                                                    |
| Bildschirmsperre und Ruhezustand auf echter Hardware | Die Logik ist per Unit-Test geprüft; die Signale (`ActiveChanged`, Uhrensprung) sind unter CachyOS nicht verifiziert.                                                                                                                                                                                                                     |
| `org.kde.plasma.workspace.dbus`                      | Kaum dokumentiert und keine zugesagte stabile API; Plasma-Updates können das Widget beschädigen.                                                                                                                                                                                                                                          |

Die [Release-Checkliste](operations.md#release-checkliste) deckt diese Punkte ab.

## Risiken

- **D-Bus-Zugriff:** Jeder Prozess der Benutzersitzung kann die Uhr über die Schnittstelle starten oder stoppen. Bewusst akzeptiert, weil ein solcher Prozess ohnehin den Secret Service lesen könnte; die Schnittstelle gibt weder Schlüssel noch rohe API-Daten preis.
- **Reichweite des API-Schlüssels:** Ein Clockodo-API-Schlüssel hat die vollen Rechte des Benutzers. Er wird nur im Secret Service gespeichert und nie geloggt.
- **Firmenspezifische Pflichtfelder:** Clockodo-Einstellungen können beim Start ein Projekt oder eine Beschreibung verlangen. Das Widget zeigt die Fehlermeldung von Clockodo an, kann diese Regeln aber vorab nicht kennen (unbekannt).
- **Unterprojekte** werden nicht unterstützt; Kontexte mit Unterprojekt werden aus der Liste der zuletzt verwendeten herausgefiltert.
- **Nicht festgelegte Build-Eingaben:** `Dockerfile.arch` verwendet `archlinux/archlinux:base-devel` ohne Digest, und die Workflows nutzen Actions über Major-Tags (`@v7`, `@v6`), während der Plan das Festlegen per Digest/Commit-SHA empfiehlt.
- **qmllint-Warnungen:** Die QML-Dateien greifen unqualifiziert auf `root` zu (aus `main.qml` oder der Konfigurationsseite). Das ist in Plasmoids üblich und funktioniert zur Laufzeit, aber qmllint kann diese Bindings nicht prüfen. Es hat auch einen falschen Eigenschaftsnamen übersehen (`separator` statt `isSeparator`), durch den das Widget nicht lud; erst ein Lauf in `plasmoidviewer` hat ihn gefunden, deshalb gehört eine Laufzeitprüfung in jede Release-Prüfung.
- **Eigenheiten des D-Bus-Moduls:** In 0.1.0 schlug jeder Aufruf mit Argumenten fehl, weil das Modul die Signatur der Argumente als ein Struct erwartet (`(ss)`, nicht `ss`); das ist nicht dokumentiert und könnte sich wieder ändern.

## Offene Punkte

Entschieden:

- Das Repository `https://github.com/jmatthiesen81/clockodo-plasma` ist öffentlich; Die Releases 0.1.0 und 0.1.1 sind dort veröffentlicht.
- Der Webserver für das pacman-Repository ist ein Debian-Server mit Plesk (nginx-Proxy vor Apache); die Veröffentlichung muss rsync als Systembenutzer der Subscription ausführen (siehe [Betrieb – Webserver](operations.md#webserver)).

| Punkt    | Frage                                                              |
| -------- | ------------------------------------------------------------------ |
| Klockodo | Prüfen, ob das vorhandene GTK-Werkzeug den Bedarf bereits abdeckt. |

## Roadmap

| Version  | Inhalt                                                                                                                                                                               |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 0.1.0    | Auf GitHub veröffentlicht (2026-11-19), Rezept fertig.                                                                                                                               |
| 0.1.1    | D-Bus-Fix und Popup-Layout; erster Lauf unter CachyOS mit echtem Konto.                                                                                                              |
| 0.2.0    | Standardbuchung mit Schnellstart/-stopp, Kontextmenü, Tagessoll, Stile in der Leiste, Konfigurationsdialog; offen: Test unter CachyOS, dann Release-Checkliste und Veröffentlichung. |
| 1.0.0    | Alle Punkte der Release-Checkliste erfüllt, Barrierefreiheit in Plasma geprüft (Tastatur, Screenreader).                                                                             |
| Nach 1.0 | Plasma-VM-Tests mit GUI-Automatisierung, Unterprojekte, OAuth 2.0, Abwesenheiten, Herkunfts-Attestation, weitere Sprachen.                                                           |

[Index](index.md) · [English](../en/findings.md)
