# Befunde

Risiken, ungetestete Bereiche und offene Punkte für Version 0.1.0 (2026-11-19).

## Noch nicht getestet

| Bereich                                              | Status                                                                                                                     |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Widget in einer echten Plasma-Sitzung                | Noch nicht ausgeführt; QML wird nur mit `qmllint` geprüft. Layout, Popup-Größe und Bindings brauchen einen manuellen Test. |
| Echtes Clockodo-Konto                                | API-Aufrufe sind nur gegen Mocks getestet, die nach der OpenAPI-Spezifikation gebaut wurden.                               |
| KWallet / Secret Service                             | Nicht gegen einen echten Anbieter getestet; die Container-Prüfung deckt nur „kein Anbieter“ ab.                            |
| Bildschirmsperre und Ruhezustand auf echter Hardware | Die Logik ist per Unit-Test geprüft; die Signale (`ActiveChanged`, Uhrensprung) sind unter CachyOS nicht verifiziert.      |
| `org.kde.plasma.workspace.dbus`                      | Kaum dokumentiert und keine zugesagte stabile API; Plasma-Updates können das Widget beschädigen.                           |

Die [Release-Checkliste](operations.md#release-checkliste) deckt diese Punkte ab.

## Risiken

- **D-Bus-Zugriff:** Jeder Prozess der Benutzersitzung kann die Uhr über die Schnittstelle starten oder stoppen. Bewusst akzeptiert, weil ein solcher Prozess ohnehin den Secret Service lesen könnte; die Schnittstelle gibt weder Schlüssel noch rohe API-Daten preis.
- **Reichweite des API-Schlüssels:** Ein Clockodo-API-Schlüssel hat die vollen Rechte des Benutzers. Er wird nur im Secret Service gespeichert und nie geloggt.
- **Firmenspezifische Pflichtfelder:** Clockodo-Einstellungen können beim Start ein Projekt oder eine Beschreibung verlangen. Das Widget zeigt die Fehlermeldung von Clockodo an, kann diese Regeln aber vorab nicht kennen (unbekannt).
- **Unterprojekte** werden nicht unterstützt; Kontexte mit Unterprojekt werden aus der Liste der zuletzt verwendeten herausgefiltert.
- **Nicht festgelegte Build-Eingaben:** `Dockerfile.arch` verwendet `archlinux/archlinux:base-devel` ohne Digest, und die Workflows nutzen Actions über Major-Tags (`@v7`, `@v6`), während der Plan das Festlegen per Digest/Commit-SHA empfiehlt.
- **qmllint-Warnungen:** Alle QML-Dateien greifen unqualifiziert auf `root` aus `main.qml` zu. Das ist bei Plasmoids üblich und funktioniert zur Laufzeit, aber qmllint kann diese Bindings nicht prüfen.

## Offene Punkte

Entschieden:

- Das Repository `https://github.com/jmatthiesen81/clockodo-plasma` ist öffentlich; Release 0.1.0 ist dort veröffentlicht.
- Der Webserver für das pacman-Repository ist ein Debian-Server mit Plesk (nginx-Proxy vor Apache); die Veröffentlichung muss rsync als Systembenutzer der Subscription ausführen (siehe [Betrieb – Webserver](operations.md#webserver)).

| Punkt                             | Frage                                                              |
| --------------------------------- | ------------------------------------------------------------------ |
| Klockodo                          | Prüfen, ob das vorhandene GTK-Werkzeug den Bedarf bereits abdeckt. |
| Secret Service auf dem Zielsystem | Standardmäßig aktiv, oder muss `apiEnabled` gesetzt werden?        |

## Roadmap

| Version  | Inhalt                                                                                                                     |
| -------- | -------------------------------------------------------------------------------------------------------------------------- |
| 0.1.0    | Auf GitHub veröffentlicht (2026-11-19), Rezept fertig; offen: Release-Checkliste auf CachyOS, dann Veröffentlichung.       |
| 1.0.0    | Alle Punkte der Release-Checkliste erfüllt, Barrierefreiheit in Plasma geprüft (Tastatur, Screenreader).                   |
| Nach 1.0 | Plasma-VM-Tests mit GUI-Automatisierung, Unterprojekte, OAuth 2.0, Abwesenheiten, Herkunfts-Attestation, weitere Sprachen. |

[Index](index.md) · [English](../en/findings.md)
