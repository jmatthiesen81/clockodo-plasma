# Einrichtung

Voraussetzungen, Installation, erster Start und Entfernen von Clockodo Plasma.

## Voraussetzungen

| Punkt               | Anforderung                                                                                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System              | CachyOS oder Arch Linux                                                                                                                                       |
| Desktop             | KDE Plasma ≥ 6.4 (das Widget benötigt den D-Bus-`SignalWatcher` aus `plasma-workspace` 6.4)                                                                   |
| Secret Service      | KWallet (`ksecretd`) oder ein anderer Anbieter von `org.freedesktop.secrets`                                                                                  |
| Clockodo            | Konto mit API-Schlüssel (Clockodo → *Persönliche Daten*)                                                                                                      |
| Paketabhängigkeiten | `python`, `python-httpx`, `python-dbus-fast`, `python-secretstorage`, `plasma-workspace>=6.4`, `libplasma`, `kirigami`, `qt6-declarative`; optional `kwallet` |

Alle Abhängigkeiten liegen in Arch `extra`.

## Installation

### Aus dem pacman-Repository

Sobald das eigene pacman-Repository in `/etc/pacman.conf` eingerichtet und das Paket veröffentlicht ist:

```bash
sudo pacman -Syu clockodo-plasma
```

### Aus einem lokalen Build

Erfordert Docker (oder Podman mit `CONTAINER_RUNTIME=podman`):

```bash
scripts/build-package.sh --check
sudo pacman -U dist/clockodo-plasma-*-any.pkg.tar.zst
```

### Installierte Dateien

| Pfad                                                                                      | Inhalt                                 |
| ----------------------------------------------------------------------------------------- | -------------------------------------- |
| `/usr/bin/clockodo-plasma-daemon`                                                         | Startskript                            |
| `/usr/lib/clockodo-plasma/clockodo_plasma/`                                               | Python-Code (nicht in `site-packages`) |
| `/usr/lib/systemd/user/clockodo-plasma.service`                                           | systemd-User-Unit                      |
| `/usr/share/dbus-1/services/io.github.jmatthiesen81.ClockodoPlasma.service`               | D-Bus-Aktivierung                      |
| `/usr/share/plasma/plasmoids/io.github.jmatthiesen81.clockodoplasma/`                     | Widget                                 |
| `/usr/share/doc/clockodo-plasma/README.md`, `/usr/share/licenses/clockodo-plasma/LICENSE` | Dokumentation, Lizenz                  |

## Erster Start

1. Rechtsklick auf die Kontrollleiste → *Miniprogramme hinzufügen …* → *Clockodo-Zeiterfassung*.
2. Auf das Widget klicken. Der Daemon startet automatisch über die D-Bus-Aktivierung.
3. Clockodo-E-Mail und API-Schlüssel eingeben und *Prüfen und speichern* drücken. Der Daemon prüft sie bei Clockodo und legt sie in KWallet ab. Der Schlüssel gewährt denselben Zugriff wie das Passwort.
4. Kunde, optional Projekt, und Leistung wählen, dann *Starten*.
5. Optional: die Konfiguration öffnen (Rechtsklick → *Clockodo-Zeiterfassung einrichten …*, oder das Zahnradsymbol) und eine Standardbuchung festlegen; danach starten und stoppen Strg + Linksklick oder ein Mittelklick die Uhr direkt.

Zeigt das Popup „Brieftasche gesperrt“, *Entsperren* drücken. Ist der Secret Service gar nicht verfügbar, siehe [Fehlerbehebung](troubleshooting.md#secret-service-nicht-verfügbar).

## Aktualisieren

```bash
sudo pacman -Syu
systemctl --user restart clockodo-plasma   # oder ab- und wieder anmelden
```

Ein laufender Daemon behält die alte Version bis zum Neustart; ein geändertes Widget wird nach einem Neustart von `plasmashell` oder einer neuen Anmeldung geladen. Das Paket gibt nach einem Upgrade diesen Hinweis aus.

## Deinstallation

```bash
sudo pacman -Rns clockodo-plasma
```

Persönliche Daten bleiben absichtlich erhalten. Um sie ebenfalls zu entfernen:

```bash
rm -r ~/.config/clockodo-plasma ~/.local/state/clockodo-plasma
secret-tool clear application clockodo-plasma   # oder den Eintrag in KWalletManager löschen
```

Auch das Widget aus der Kontrollleiste entfernen; sonst bleibt es als defektes Widget zurück.

[Index](index.md) · [English](../en/setup.md)
