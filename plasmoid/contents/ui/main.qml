// SPDX-License-Identifier: MPL-2.0
/*
    Clockodo Plasma – panel widget.

    All logic lives in the background daemon (D-Bus name below). The widget
    only shows the published state and forwards user actions; it never books
    anything on its own.
*/

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.plasma.workspace.dbus as DBus
import "translations.js" as Translations

PlasmoidItem {
    id: root

    readonly property string dbusService: "io.github.jmatthiesen81.ClockodoPlasma"
    readonly property string dbusPath: "/io/github/jmatthiesen81/ClockodoPlasma"
    readonly property string dbusInterface: dbusService

    // State published by the daemon (see backend/clockodo_plasma/state.py).
    property var daemonState: ({ "status": "unknown" })
    property double receivedAt: 0
    property bool daemonReachable: true
    property double nowMs: Date.now()

    readonly property string status: daemonState.status || "unknown"
    readonly property bool running: status === "running"
    readonly property bool hasData: status === "running" || status === "stopped"
    readonly property bool busy: !!daemonState.action_pending
    readonly property bool stale: !daemonReachable || !!daemonState.stale || !hasData

    // Daily total, advanced locally between updates while the clock runs.
    readonly property int todaySeconds: {
        let seconds = daemonState.today_seconds || 0;
        if (running && receivedAt > 0) {
            seconds += Math.max(0, Math.floor((nowMs - receivedAt) / 1000));
        }
        return seconds;
    }

    function formatDuration(seconds) {
        const minutes = Math.floor(Math.max(0, seconds) / 60);
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return (h < 10 ? "0" + h : String(h)) + ":" + (m < 10 ? "0" + m : String(m));
    }

    function formatTime(iso) {
        if (!iso) {
            return "";
        }
        return Qt.formatTime(new Date(iso), Qt.locale().timeFormat(Locale.ShortFormat));
    }

    // Language of the widget: chosen in the settings and resolved by the daemon
    // ("system" -> session language, English if unsupported). Until the daemon
    // answers, the session language is used.
    readonly property string language: daemonState.language || systemLanguage()

    function systemLanguage() {
        const code = Qt.locale().name.split("_")[0];
        return Translations.catalogs[code] ? code : "en";
    }

    function tr(text, arg1, arg2) {
        let args = [];
        if (arg1 !== undefined) {
            args.push(arg1);
        }
        if (arg2 !== undefined) {
            args.push(arg2);
        }
        return Translations.translate(language, text, args);
    }

    function trp(singular, plural, n) {
        return Translations.translatePlural(language, singular, plural, n);
    }

    readonly property string totalText: hasData ? formatDuration(todaySeconds) : "--:--"

    function applyState(json) {
        try {
            daemonState = JSON.parse(json);
            receivedAt = Date.now();
            nowMs = receivedAt;
            daemonReachable = true;
        } catch (e) {
            console.warn("clockodo-plasma: invalid state", e);
        }
    }

    // Calls a daemon method with string arguments; callbacks get the parsed JSON
    // result (or the raw string) resp. an error message.
    //
    // The Plasma D-Bus module encodes the whole argument list as ONE value of
    // the given signature, so the in-arguments must be wrapped as a struct:
    // "(ss)", not "ss". With "ss" only the first type is used, the list is
    // converted to a single string and the call goes out without arguments
    // ("... with signature "" could not be found").
    function call(member, args, onDone, onError) {
        const stringArgs = (args || []).map(a => new DBus.string(String(a)));
        DBus.SessionBus.asyncCall({
            "service": dbusService,
            "path": dbusPath,
            "iface": dbusInterface,
            "member": member,
            "arguments": stringArgs,
            "signature": stringArgs.length > 0 ? "(" + "s".repeat(stringArgs.length) + ")" : ""
        }, reply => {
            daemonReachable = true;
            if (onDone) {
                let value = reply.value;
                try {
                    value = JSON.parse(value);
                } catch (e) {
                    // plain string result
                }
                onDone(value);
            }
        }, reply => {
            const message = reply && reply.error ? reply.error.message : "D-Bus error";
            console.warn("clockodo-plasma:", member, message);
            if (member === "GetState") {
                daemonReachable = false;
            }
            if (onError) {
                onError(message);
            }
        });
    }

    function fetchState() {
        call("GetState", [], value => {
            if (typeof value === "object") {
                applyState(JSON.stringify(value));
            }
        });
    }

    function refresh() {
        call("Refresh", []);
    }

    // Starts the daemon via D-Bus activation and requests a fresh sync.
    Component.onCompleted: {
        fetchState();
        refresh();
    }

    onExpandedChanged: {
        if (expanded) {
            fetchState();
            refresh();
        }
    }

    DBus.SignalWatcher {
        busType: DBus.BusType.Session
        service: root.dbusService
        path: root.dbusPath
        iface: root.dbusInterface

        function dbusStateChanged(json) {
            root.applyState(String(json));
        }
    }

    DBus.DBusServiceWatcher {
        id: serviceWatcher
        busType: DBus.BusType.Session
        watchedService: root.dbusService
        onRegisteredChanged: {
            if (registered) {
                root.fetchState();
            } else {
                root.daemonReachable = false;
            }
        }
    }

    Timer {
        // Advances the displayed total; the daemon corrects it every minute.
        interval: 10000
        repeat: true
        running: root.running
        onTriggered: root.nowMs = Date.now()
    }

    Timer {
        // Fallback: re-read the state if no signal arrived for a while.
        interval: 120000
        repeat: true
        running: true
        onTriggered: root.fetchState()
    }

    Plasmoid.icon: running ? "media-playback-pause" : "media-playback-start"
    Plasmoid.status: running ? PlasmaCore.Types.ActiveStatus : PlasmaCore.Types.PassiveStatus

    toolTipMainText: running
        ? root.tr("Clock running – today %1", totalText)
        : root.tr("Clock stopped – today %1", totalText)
    toolTipSubText: {
        if (!daemonReachable) {
            return root.tr("Background service not reachable");
        }
        let parts = [];
        if (running && daemonState.running) {
            parts.push(daemonState.running.label);
        }
        if (daemonState.error) {
            parts.push(daemonState.error);
        }
        if (daemonState.last_sync) {
            parts.push(root.tr("Last update: %1", formatTime(daemonState.last_sync)));
        }
        return parts.join("\n");
    }

    preferredRepresentation: compactRepresentation
    compactRepresentation: CompactRepresentation {}
    fullRepresentation: FullRepresentation {}

    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            text: root.tr("Refresh")
            icon.name: "view-refresh"
            onTriggered: root.refresh()
        }
    ]
}
