.pragma library
// SPDX-License-Identifier: MPL-2.0

// Translations of the widget, keyed by the English source text.
// English needs no catalog. A new language needs a catalog here and an entry
// in LANGUAGES of backend/clockodo_plasma/messages.py; the tests check that
// every string used in the QML files is translated.
// Plural entries are keyed "singular|plural" and hold [one, other].

const catalogs = {
    "de": {
        "– no project –": "– ohne Projekt –",
        "Recently used": "Zuletzt verwendet",
        "Choose a recent context…": "Zuletzt verwendeten Kontext wählen …",
        "Customer:": "Kunde:",
        "Choose…": "Auswählen …",
        "Customer": "Kunde",
        "Project:": "Projekt:",
        "Project": "Projekt",
        "Service:": "Leistung:",
        "Service": "Leistung",
        "Enter your Clockodo e-mail address and API key. You find the key in Clockodo under \"Personal data\". The key grants the same access as your password and is stored in the wallet.": "Gib deine Clockodo-E-Mail-Adresse und deinen API-Key ein. Den Key findest du in Clockodo unter \"Persönliche Daten\". Er gewährt denselben Zugriff wie dein Passwort und wird in der Brieftasche (KWallet) gespeichert.",
        "E-mail:": "E-Mail:",
        "E-mail": "E-Mail",
        "API key:": "API-Key:",
        "API key": "API-Key",
        "Check and save": "Prüfen und speichern",
        "Settings": "Einstellungen",
        "Clockodo": "Clockodo",
        "Refresh": "Aktualisieren",
        "Back": "Zurück",
        "The background service is not reachable. Check \"systemctl --user status clockodo-plasma\".": "Der Hintergrunddienst ist nicht erreichbar. Bitte \"systemctl --user status clockodo-plasma\" prüfen.",
        "Your Clockodo time zone (%1) differs from this computer's. \"Today\" follows Clockodo.": "Deine Clockodo-Zeitzone (%1) weicht von der dieses Rechners ab. \"Heute\" richtet sich nach Clockodo.",
        "Clock is running": "Uhr läuft",
        "Clock is stopped": "Uhr ist gestoppt",
        "%1 – since %2": "%1 – seit %2",
        "Work time today: %1": "Arbeitszeit heute: %1",
        "Language:": "Sprache:",
        "Language": "Sprache",
        "today": "heute",
        "Outdated – last update %1": "Veraltet – letzte Aktualisierung %1",
        "Stop": "Stoppen",
        "Switch…": "Wechseln …",
        "Description (optional)": "Beschreibung (optional)",
        "Book on: %1": "Buchen auf: %1",
        "Please choose customer and service.": "Bitte Kunde und Leistung auswählen.",
        "Switch to this": "Hierauf wechseln",
        "Start": "Starten",
        "Cancel": "Abbrechen",
        "Your Clockodo credentials are stored in the wallet, which is locked.": "Deine Clockodo-Zugangsdaten liegen in der Brieftasche (KWallet), die gesperrt ist.",
        "Unlock": "Entsperren",
        "Connecting to Clockodo…": "Verbinde mit Clockodo …",
        "Off": "Aus",
        "30 seconds": "30 Sekunden",
        "1 minute": "1 Minute",
        "2 minutes": "2 Minuten",
        "5 minutes": "5 Minuten",
        "Update every:": "Aktualisieren alle:",
        "Update interval": "Aktualisierungsintervall",
        "Reminders:": "Erinnerungen:",
        "Notify when the screen is locked while the clock runs": "Benachrichtigen, wenn der Bildschirm bei laufender Uhr gesperrt wird",
        "Remind after hours of running clock": "Nach Stunden laufender Uhr erinnern",
        "no reminder for long-running clocks": "keine Erinnerung bei lange laufender Uhr",
        "remind after %1 hour|remind after %1 hours": [
            "nach %1 Stunde erinnern",
            "nach %1 Stunden erinnern"
        ],
        "Contact e-mail:": "Kontakt-E-Mail:",
        "default: your Clockodo e-mail": "Standard: deine Clockodo-E-Mail",
        "Contact e-mail for the Clockodo API": "Kontakt-E-Mail für die Clockodo-API",
        "Clockodo requires a technical contact address for every API client.": "Clockodo verlangt für jede API-Anwendung eine technische Kontaktadresse.",
        "Save": "Speichern",
        "Change Clockodo account or API key…": "Clockodo-Konto oder API-Key ändern …",
        "Clock running – today %1": "Uhr läuft – heute %1",
        "Clock stopped – today %1": "Uhr gestoppt – heute %1",
        "Background service not reachable": "Hintergrunddienst nicht erreichbar",
        "Last update: %1": "Letzte Aktualisierung: %1"
    }
};

function format(text, args) {
    let result = text;
    for (let i = 0; i < args.length; ++i) {
        result = result.split("%" + (i + 1)).join(String(args[i]));
    }
    return result;
}

function translate(language, text, args) {
    const catalog = catalogs[language];
    const translated = catalog && typeof catalog[text] === "string" ? catalog[text] : text;
    return format(translated, args || []);
}

function translatePlural(language, singular, plural, n) {
    const catalog = catalogs[language];
    const forms = catalog ? catalog[singular + "|" + plural] : null;
    // English and German both use "one" for n == 1 and "other" otherwise.
    const one = n === 1;
    const text = forms ? (one ? forms[0] : forms[1]) : (one ? singular : plural);
    return format(text, [n]);
}
