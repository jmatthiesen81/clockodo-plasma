# Betrieb

Daemon betreiben, beobachten und aktualisieren sowie das Paket bauen, freigeben und veröffentlichen.

## Daemon

```bash
systemctl --user status clockodo-plasma
systemctl --user restart clockodo-plasma
journalctl --user -u clockodo-plasma -f
```

- Der Daemon loggt nach stderr, das systemd ins Journal schreibt. Header, Request- und Response-Bodys, Kundennamen und Beschreibungen werden nie geloggt; registrierte Geheimnisse werden als zweite Absicherung durch `***` ersetzt.
- Für ausführliche Logs den Daemon nach dem Stoppen der Unit von Hand starten: `systemctl --user stop clockodo-plasma && clockodo-plasma-daemon --debug`.
- `clockodo-plasma-daemon --version` gibt die installierte Version aus.
- Nur ein Daemon kann den Bus-Namen besitzen; eine zweite Instanz beendet sich mit Exit-Code 1.

Zustand auf dem Bus ansehen:

```bash
busctl --user call io.github.jmatthiesen81.ClockodoPlasma /io/github/jmatthiesen81/ClockodoPlasma \
    io.github.jmatthiesen81.ClockodoPlasma GetState
```

## Paket bauen und prüfen

```bash
scripts/build-package.sh          # nur bauen → dist/clockodo-plasma-<version>-<rel>-any.pkg.tar.zst
scripts/build-package.sh --check  # bauen und prüfen
```

[build-package.sh](../../scripts/build-package.sh) baut das Image aus [Dockerfile.arch](../../Dockerfile.arch), bindet den Checkout schreibgeschützt ein, kopiert ihn für den unprivilegierten Benutzer `builder` und führt `makepkg` mit dem Entwicklungs-[PKGBUILD](../../packaging/arch/PKGBUILD) aus. Container laufen mit `--rm`. [check-package.sh](../../scripts/check-package.sh) prüft anschließend als root im Container:

1. Paketmetadaten und erforderliche Dateien, und dass nichts in `site-packages` landet,
2. `namcap` (nur Warnungen),
3. Testinstallation mit `pacman -U`,
4. `clockodo-plasma-daemon --version` entspricht der Paketversion,
5. D-Bus-Aktivierung auf einem privaten Session-Bus beantwortet `GetState` (erwartet `secret_locked`, da der Container keinen Secret Service hat),
6. `qmllint` auf dem installierten QML (Fehler lassen die Prüfung scheitern; Warnungen über unqualifizierten Zugriff auf `root` sind erwartet),
7. Entfernen mit `pacman -R`.

[install-files.sh](../../scripts/install-files.sh) ist der einzige Ort, der das installierte Layout kennt; das Entwicklungs-PKGBUILD und das Release-Rezept des pacman-Repositorys rufen es beide auf.

## Release

Releases folgen Semantic Versioning; Tags haben kein Präfix `v`. Änderungen werden unter `## [Unreleased]` in [CHANGELOG.md](../../CHANGELOG.md) gesammelt.

```bash
scripts/release.sh 0.1.0 --dry-run   # Vorschau
scripts/release.sh 0.1.0             # Versionen setzen, Changelog datieren, committen, taggen
git push origin canon
git push origin 0.1.0
```

[release.sh](../../scripts/release.sh):

- schreibt die Version nach `backend/clockodo_plasma/__init__.py`, `plasmoid/metadata.json` und `packaging/arch/PKGBUILD` (und setzt `pkgrel` auf 1 zurück),
- macht aus `[Unreleased]` den Abschnitt `## [X.Y.Z] - <Datum>`, fügt einen neuen leeren Abschnitt `[Unreleased]` hinzu und aktualisiert die Vergleichslinks (das erste Release verlinkt auf seine Release-Seite),
- committet `chore(release): X.Y.Z` und erstellt ein annotiertes Tag; es wird nichts gepusht.

Ein Pre-Release `X.Y.Z-rc.N` setzt in den Dateien die Basisversion `X.Y.Z` (`pkgver` von pacman erlaubt kein `-`) und lässt das Changelog unverändert.

Das Pushen des Tags startet [release.yml](../../.github/workflows/release.yml): Prüfung von Version und Changelog, Tests, Paketprüfung, dann ein GitHub-Release „Clockodo Plasma X.Y.Z“ mit `clockodo-plasma-X.Y.Z.tar.gz` (aus `git archive`) und `SHA256SUMS`. Die Release-Notes bestehen aus dem Changelog-Abschnitt ([changelog-section.sh](../../scripts/changelog-section.sh)), gefolgt von den von GitHub erzeugten Notes. Tags mit Suffix werden zu Pre-Releases.

## Release-Checkliste

Bevor ein Release im pacman-Repository veröffentlicht wird, auf einem CachyOS-Rechner mit Plasma ≥ 6.4 und echtem Clockodo-Konto prüfen:

- [ ] Installation mit pacman aus dem eigenen Repository funktioniert; Paket- und Repository-Signaturen werden geprüft.
- [ ] Das Widget erscheint; Play/Pause und Tagessumme sind immer sichtbar; veraltete Daten sind erkennbar.
- [ ] Ein Klick öffnet das Popup und synchronisiert sofort.
- [ ] Starten, Stoppen und Wechseln funktionieren; der Buchungskontext ist vor dem Start sichtbar.
- [ ] Eine auf einem anderen Gerät gestartete Uhr wird nie stillschweigend gestoppt; Änderungen anderer Geräte werden erkannt.
- [ ] Doppelklicks und verlorene Antworten führen zu keinen doppelten oder falschen Buchungen; Netzwerkfehler buchen nichts.
- [ ] Die Tagessumme stimmt mit Clockodo überein, auch nach Neustart und nachträglichen Korrekturen; Tageswechsel, Sommerzeit und eine abweichende Clockodo-Zeitzone werden berücksichtigt.
- [ ] Der API-Key liegt in KWallet und in keinem Log; gesperrte Brieftasche und abgelehnter Key werden verständlich erklärt.
- [ ] Die Erinnerung bei Bildschirmsperre funktioniert; Ruhezustand/Aufwachen löst eine Synchronisierung aus.
- [ ] Intervall und Sprache lassen sich ändern.
- [ ] Ein Paketupdate behält Einstellungen und Widget-Position; ein Python-Minor-Update von Arch bricht das Paket nicht.
- [ ] Die Deinstallation entfernt die Programmdateien und nennt die verbleibenden Benutzerdaten.

Die automatisierten Teile (Unit- und D-Bus-Tests, Paketbau als Nicht-Root, Prüfung von Inhalt und Abhängigkeiten, Release-Tarball mit `SHA256SUMS`) laufen in der CI.

## Veröffentlichung im pacman-Repository

GitHub-Releases enthalten **kein Binärpaket**. Das installierbare Paket wird vom separaten Repository-Build-Projekt (`cachyos-repository`) aus dem Release-Tarball gebaut und dort signiert. Gründe:

- makepkg-Builds sind nicht byte-gleich (Build-Datum, `PACKAGER`, `.BUILDINFO`). Zwei Pakete mit gleichem Dateinamen, aber anderem Inhalt (eines von GitHub, eines aus dem Repository) kollidierten im pacman-Cache, und `pacman -Syu` scheiterte an Prüfsumme oder Signatur.
- Der Signaturschlüssel des Repositorys signiert auch alle anderen Pakete darin und darf nie zu GitHub; er bleibt auf dem Signaturrechner.
- Ein zweites pacman-Repository mit gleichem Paketnamen würde je nach Reihenfolge in `pacman.conf` gewinnen oder verlieren.

Schritte in `cachyos-repository`:

1. `scripts/update-recipe.sh --check` findet das neue GitHub-Release.
2. `scripts/update-recipe.sh clockodo-plasma` setzt `pkgver`, `pkgrel=1` und `sha256sums` und gleicht sie mit `SHA256SUMS` des Releases ab.
3. `scripts/build.sh clockodo-plasma` (die Verifikation läuft automatisch), dann `scripts/publish.sh clockodo-plasma`.
4. Auf dem Signaturrechner: `scripts/sign-repo.sh` mit `SIGN_REMOTE` auf den Build-Server.
5. Übertragung zum Webserver in zwei Durchgängen (erst Pakete, dann die Datenbank mit `--delete`).
6. Smoke-Test auf CachyOS: `sudo pacman -Syu clockodo-plasma`.

Pre-Releases werden nicht im pacman-Repository veröffentlicht (dessen Aufbewahrung sortiert mit `sort --version-sort`, nicht mit `vercmp`).

### Rezept in `cachyos-repository`

- `recipes/clockodo-plasma/PKGBUILD`: Quelle = Release-Tarball `clockodo-plasma-X.Y.Z.tar.gz`, `sha256sums`, `package()` ruft `scripts/install-files.sh "$pkgdir" /usr` auf. Bei jedem Release `depends=()` mit [packaging/arch/PKGBUILD](../../packaging/arch/PKGBUILD) abgleichen.
- `recipes/clockodo-plasma/clockodo-plasma.install`: Kopie von [packaging/arch/clockodo-plasma.install](../../packaging/arch/clockodo-plasma.install); synchron halten.
- `recipes/clockodo-plasma/verify.sh`: prüft die installierten Dateien, dass nichts in `site-packages` liegt, die Versionen von Daemon und Plasmoid, die D-Bus-Aktivierung auf einem privaten Session-Bus (`GetState` antwortet `secret_locked`) und `qmllint`.
- `scripts/update-recipe.sh`: `--check` liest das neueste Release über die GitHub-Releases-API, `update-recipe.sh clockodo-plasma` lädt den Tarball und gleicht seine sha256 mit `SHA256SUMS` des Releases ab.
- Dort noch offen: Basis-Image in `build.conf` per Digest pinnen.

### Webserver

Das pacman-Repository liefert ein Debian-Server mit Plesk aus; Plesks nginx läuft als Reverse-Proxy vor Apache. Das Repository liegt im Webspace einer Subscription, die Dateien gehören deren Systembenutzer.

- rsync als **Systembenutzer der Subscription** ausführen (prüfen, ob dessen SSH-Shell rsync bereitstellt). Sonst ändern sich die Eigentümer, Plesk kann die Dateien nicht mehr verwalten und die Symlinks werden nicht ausgeliefert.
- Symlinks `<repo>.db` / `<repo>.files`: nginx (mit „Smart static files processing“) wendet `disable_symlinks if_not_owner` an, Apache `SymLinksIfOwnerMatch`. Symlink und Ziel müssen demselben Benutzer gehören; das ist gegeben, wenn rsync als Subscription-Benutzer läuft (Annahme nach Plesk-Standardverhalten, auf dem Server prüfen).
- Basic Auth bei Bedarf über Plesks „Passwortgeschützte Verzeichnisse“.
- `Cache-Control: no-cache` für Datenbank und Signaturen sowie die Sperre von Dotfiles als zusätzliche nginx-Direktiven (oder Apache-Direktiven, falls Apache die Dateien ausliefert).

[Index](index.md) · [English](../en/operations.md)
