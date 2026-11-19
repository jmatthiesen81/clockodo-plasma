# SPDX-License-Identifier: MPL-2.0
"""User-facing texts of the daemon.

The language is chosen in the settings: "system" (default) follows the
session's LANGUAGE / LC_ALL / LC_MESSAGES / LANG and falls back to English if
none of them names a supported language.
"""

from __future__ import annotations

import os

MESSAGES: dict[str, dict[str, str]] = {
    "not_configured": {
        "en": "Please enter your Clockodo e-mail and API key.",
        "de": "Bitte Clockodo-E-Mail und API-Key eingeben.",
    },
    "secret_locked": {
        "en": "The wallet is locked. Unlock it to access Clockodo.",
        "de": "Die Brieftasche ist gesperrt. Zum Zugriff auf Clockodo bitte entsperren.",
    },
    "secret_unavailable": {
        "en": "No Secret Service available (KWallet). Credentials cannot be read.",
        "de": "Kein Secret Service verfügbar (KWallet). Zugangsdaten können nicht gelesen werden.",
    },
    "auth_failed": {
        "en": "Clockodo rejected the API key. Please enter a new one "
        "(a password change invalidates the key).",
        "de": "Clockodo hat den API-Key abgelehnt. Bitte neu eingeben "
        "(eine Passwortänderung macht den Key ungültig).",
    },
    "auth_failed_title": {
        "en": "Clockodo: API key rejected",
        "de": "Clockodo: API-Key abgelehnt",
    },
    "network": {
        "en": "Clockodo is not reachable. Showing the last known state.",
        "de": "Clockodo ist nicht erreichbar. Angezeigt wird der letzte bekannte Stand.",
    },
    "rate_limited": {
        "en": "Too many requests to Clockodo, retrying later.",
        "de": "Zu viele Anfragen an Clockodo, neuer Versuch später.",
    },
    "server_error": {
        "en": "Clockodo reported an error: {detail}",
        "de": "Clockodo meldet einen Fehler: {detail}",
    },
    "busy": {
        "en": "Another action is still running.",
        "de": "Eine andere Aktion läuft noch.",
    },
    "not_ready": {
        "en": "Not connected to Clockodo yet.",
        "de": "Noch nicht mit Clockodo verbunden.",
    },
    "invalid_context": {
        "en": "The booking context is incomplete or no longer active: {detail}",
        "de": "Der Buchungskontext ist unvollständig oder nicht mehr aktiv: {detail}",
    },
    "already_running": {
        "en": "A clock is already running: {label} (since {since}). Nothing was started.",
        "de": "Es läuft bereits eine Uhr: {label} (seit {since}). Es wurde nichts gestartet.",
    },
    "started": {
        "en": "Clock started: {label}",
        "de": "Uhr gestartet: {label}",
    },
    "stopped": {
        "en": "Clock stopped.",
        "de": "Uhr gestoppt.",
    },
    "switched": {
        "en": "Switched to: {label}",
        "de": "Gewechselt zu: {label}",
    },
    "start_stopped_other": {
        "en": "Clockodo stopped a running clock while starting: {label}",
        "de": "Clockodo hat beim Start eine laufende Uhr gestoppt: {label}",
    },
    "truncated": {
        "en": "The stopped entry was truncated to 24 hours.",
        "de": "Der gestoppte Eintrag wurde auf 24 Stunden gekürzt.",
    },
    "clockodo_note": {
        "en": "Note from Clockodo: {detail}",
        "de": "Hinweis von Clockodo: {detail}",
    },
    "outcome_unknown": {
        "en": "The answer from Clockodo was lost. The state was reloaded: {result}",
        "de": "Die Antwort von Clockodo ging verloren. Der Stand wurde neu geladen: {result}",
    },
    "result_running": {
        "en": "clock is running ({label})",
        "de": "Uhr läuft ({label})",
    },
    "result_stopped": {
        "en": "clock is stopped",
        "de": "Uhr ist gestoppt",
    },
    "network_nothing_booked": {
        "en": "Clockodo is not reachable. Nothing was booked.",
        "de": "Clockodo ist nicht erreichbar. Es wurde nichts gebucht.",
    },
    "stale_entry": {
        "en": "The displayed state was outdated and has been reloaded. Nothing was changed.",
        "de": "Der angezeigte Stand war veraltet und wurde neu geladen. Es wurde nichts geändert.",
    },
    "switch_not_running": {
        "en": "The clock is no longer running (stopped elsewhere). Nothing was started.",
        "de": "Die Uhr läuft nicht mehr (anderswo gestoppt). Es wurde nichts gestartet.",
    },
    "external_started": {
        "en": "A clock was started elsewhere: {label}",
        "de": "Anderswo wurde eine Uhr gestartet: {label}",
    },
    "external_stopped": {
        "en": "The clock was stopped elsewhere.",
        "de": "Die Uhr wurde anderswo gestoppt.",
    },
    "credentials_saved": {
        "en": "Connected as {name}.",
        "de": "Verbunden als {name}.",
    },
    "credentials_wrong": {
        "en": "E-mail or API key is wrong.",
        "de": "E-Mail oder API-Key ist falsch.",
    },
    "credentials_incomplete": {
        "en": "Please enter e-mail and API key.",
        "de": "Bitte E-Mail und API-Key eingeben.",
    },
    "unlock_failed": {
        "en": "The wallet was not unlocked.",
        "de": "Die Brieftasche wurde nicht entsperrt.",
    },
    "settings_saved": {
        "en": "Settings saved.",
        "de": "Einstellungen gespeichert.",
    },
    "language_system": {
        "en": "System language",
        "de": "Systemsprache",
    },
    "settings_invalid": {
        "en": "Invalid settings: {detail}",
        "de": "Ungültige Einstellungen: {detail}",
    },
    "reminder_lock_title": {
        "en": "Clockodo: clock is still running",
        "de": "Clockodo: Uhr läuft noch",
    },
    "reminder_lock_body": {
        "en": "{label}, since {since}",
        "de": "{label}, seit {since}",
    },
    "reminder_long_title": {
        "en": "Clockodo: clock running for more than {hours} h",
        "de": "Clockodo: Uhr läuft seit über {hours} Std.",
    },
    "no_default": {
        "en": "No default booking is set. Please choose customer and service.",
        "de": "Keine Standardbuchung festgelegt. Bitte Kunde und Leistung auswählen.",
    },
    "quick_failed_title": {
        "en": "Clockodo: action failed",
        "de": "Clockodo: Aktion fehlgeschlagen",
    },
    "overtime_title": {
        "en": "Clockodo: daily target exceeded",
        "de": "Clockodo: Tagessoll überschritten",
    },
    "overtime_body": {
        "en": "{total} of {target} – the clock is still running on {label}.",
        "de": "{total} von {target} – die Uhr läuft noch auf {label}.",
    },
    "action_stop": {
        "en": "Stop",
        "de": "Stoppen",
    },
    "action_continue": {
        "en": "Keep running",
        "de": "Weiterlaufen lassen",
    },
    "reminder_resume_title": {
        "en": "Clockodo: clock kept running during suspend",
        "de": "Clockodo: Uhr lief während des Ruhezustands weiter",
    },
    "reminder_resume_body": {
        "en": "Suspended for {minutes} min. {label}",
        "de": "Ruhezustand: {minutes} Min. {label}",
    },
}


# Supported languages with their native names; "en" is the fallback.
# A new language needs an entry here, in every MESSAGES entry and in
# plasmoid/contents/ui/translations.js (tests check completeness).
LANGUAGES: dict[str, str] = {"en": "English", "de": "Deutsch"}
FALLBACK = "en"
SYSTEM = "system"


def system_language(environ: dict[str, str] | None = None) -> str:
    """First supported language of the session (gettext order), else English."""
    env = os.environ if environ is None else environ
    candidates: list[str] = []
    candidates += [x for x in env.get("LANGUAGE", "").split(":") if x]
    candidates += [env.get(var, "") for var in ("LC_ALL", "LC_MESSAGES", "LANG")]
    for value in candidates:
        code = value.split(".")[0].split("@")[0].split("_")[0].lower()
        if code in LANGUAGES:
            return code
    return FALLBACK


def resolve_language(setting: str, environ: dict[str, str] | None = None) -> str:
    if setting in LANGUAGES:
        return setting
    return system_language(environ)


_current = resolve_language(SYSTEM)


def set_language(language: str) -> None:
    global _current
    _current = language if language in LANGUAGES else FALLBACK


def current_language() -> str:
    return _current


def t(key: str, **kwargs: object) -> str:
    entry = MESSAGES.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry[FALLBACK]
    return text.format(**kwargs) if kwargs else text
