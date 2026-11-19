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

PlasmoidItem {
    id: root

    DaemonClient {
        id: daemon
        language: root.daemonState.language || systemLanguage()
        onReachableChanged: reachable => {
            root.daemonReachable = reachable;
        }
    }

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

    // Panel and mouse settings (configuration dialog, stored by the daemon).
    readonly property var ui: daemonState.ui || ({})
    readonly property string panelStyle: ui.panel_style || "ring"

    // Default booking and recently used contexts, with names.
    readonly property var quick: daemonState.quick || null
    readonly property bool quickValid: !!quick && !!quick.valid
    readonly property var recent: daemonState.recent || []
    // Recent contexts that make sense as a target now (not the running one).
    readonly property var recentChoices: recent.filter(ctx => !(running && sameContext(ctx, daemonState.running)))

    // Daily total, advanced locally between updates while the clock runs.
    readonly property int todaySeconds: {
        let seconds = daemonState.today_seconds || 0;
        if (running && receivedAt > 0) {
            seconds += Math.max(0, Math.floor((nowMs - receivedAt) / 1000));
        }
        return seconds;
    }
    readonly property int targetSeconds: daemonState.target_seconds || 0
    readonly property bool overtime: hasData && targetSeconds > 0 && todaySeconds > targetSeconds
    readonly property real progress: targetSeconds > 0 ? todaySeconds / targetSeconds : -1

    // Colours: running green, stopped orange, over target red (theme colours).
    readonly property color stateColor: {
        if (!hasData) {
            return Kirigami.Theme.disabledTextColor;
        }
        if (overtime && ui.overtime_color !== false) {
            return Kirigami.Theme.negativeTextColor;
        }
        return running ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.neutralTextColor;
    }
    readonly property color panelColor: {
        if (!hasData) {
            return Kirigami.Theme.textColor;
        }
        if (overtime && ui.overtime_color !== false) {
            return Kirigami.Theme.negativeTextColor;
        }
        return ui.colorize === false ? Kirigami.Theme.textColor : stateColor;
    }

    // Result of the last action, shown in the popup.
    property string actionMessage: ""
    property bool actionOk: true
    // Incremented to ask the popup for the picker ("start/switch with selection").
    property int pickerRequest: 0

    function tr(text, arg1, arg2) {
        return daemon.tr(text, arg1, arg2);
    }

    function trp(singular, plural, n) {
        return daemon.trp(singular, plural, n);
    }

    function call(member, args, onDone, onError) {
        daemon.call(member, args, onDone, onError);
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

    readonly property string language: daemon.language
    readonly property string totalText: hasData ? formatDuration(todaySeconds) : "--:--"
    readonly property string sinceText: running && daemonState.running ? formatTime(daemonState.running.time_since) : ""

    function sameContext(a, b) {
        if (!a || !b) {
            return false;
        }
        return a.customers_id === b.customers_id
            && (a.projects_id || 0) === (b.projects_id || 0)
            && a.services_id === b.services_id;
    }

    function contextData(ctx, text) {
        return {
            "customers_id": ctx.customers_id,
            "projects_id": ctx.projects_id || null,
            "services_id": ctx.services_id,
            "text": (text !== undefined ? text : ctx.text) || null
        };
    }

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

    // Results of actions started outside the popup open it when they failed,
    // so the message is not lost.
    function showResult(result, openOnError) {
        actionOk = !!(result && result.ok);
        actionMessage = result && result.message ? result.message : "";
        if (!actionOk && openOnError) {
            root.expanded = true;
        }
    }

    function showError(message, openOnError) {
        showResult({ "ok": false, "message": message }, openOnError);
    }

    // Stop the shown entry, or start the default booking. Without a default
    // booking the picker opens instead.
    function quickToggle() {
        if (!hasData || busy) {
            return;
        }
        const seen = running && daemonState.running ? daemonState.running.entry_id : "";
        actionMessage = "";
        call("QuickToggle", [seen], result => {
            if (result && result.needs_picker) {
                openPicker();
            } else {
                showResult(result, false); // the daemon notifies about failures
            }
        }, message => showError(message, true));
    }

    function openPicker() {
        pickerRequest += 1;
        root.expanded = true;
    }

    function startContext(ctx, text, openOnError) {
        actionMessage = "";
        call("Start", [JSON.stringify(contextData(ctx, text))],
             result => showResult(result, openOnError),
             message => showError(message, openOnError));
    }

    function switchTo(ctx, text, openOnError) {
        if (!running || !daemonState.running) {
            return;
        }
        actionMessage = "";
        call("Switch", [JSON.stringify(contextData(ctx, text)), daemonState.running.entry_id],
             result => showResult(result, openOnError),
             message => showError(message, openOnError));
    }

    function startOrSwitch(ctx, openOnError) {
        if (running) {
            switchTo(ctx, undefined, openOnError);
        } else {
            startContext(ctx, undefined, openOnError);
        }
    }

    // "quick", "picker" or "none" – configured for modifier + left click and middle click.
    function runClickAction(action) {
        if (action === "quick") {
            quickToggle();
        } else if (action === "picker") {
            openPicker();
        }
    }

    // Starts the daemon via D-Bus activation and requests a fresh sync.
    Component.onCompleted: {
        fetchState();
        refresh();
    }

    onExpandedChanged: {
        if (root.expanded) {
            fetchState();
            refresh();
        }
    }

    DBus.SignalWatcher {
        busType: DBus.BusType.Session
        service: daemon.service
        path: daemon.path
        iface: daemon.iface

        function dbusStateChanged(json) {
            root.applyState(String(json));
        }
    }

    DBus.DBusServiceWatcher {
        busType: DBus.BusType.Session
        watchedService: daemon.service
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

    Plasmoid.icon: "chronometer"
    Plasmoid.status: running ? PlasmaCore.Types.ActiveStatus : PlasmaCore.Types.PassiveStatus

    toolTipMainText: {
        if (overtime) {
            return root.tr("Over daily target – today %1 of %2", totalText, formatDuration(targetSeconds));
        }
        return running
            ? root.tr("Clock running – today %1", totalText)
            : root.tr("Clock stopped – today %1", totalText);
    }
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

    // ------------------------------------------------------------ context menu

    PlasmaCore.Action {
        id: statusAction
        enabled: false
        text: {
            if (!root.hasData) {
                return root.tr("Clockodo – not connected");
            }
            return root.running
                ? root.tr("Running since %1 · %2 today", root.sinceText, root.totalText)
                : root.tr("Stopped · %1 today", root.totalText);
        }
    }

    PlasmaCore.Action {
        id: quickAction
        enabled: root.hasData && !root.busy
        icon.name: root.running ? "media-playback-stop" : "media-playback-start"
        text: {
            if (root.running) {
                return root.tr("Stop");
            }
            return root.quickValid && root.quick.label
                ? root.tr("Quick start: %1", root.quick.label)
                : root.tr("Quick start");
        }
        onTriggered: root.quickToggle()
    }

    PlasmaCore.Action {
        id: switchDefaultAction
        visible: root.running && root.quickValid && !root.sameContext(root.quick, root.daemonState.running)
        enabled: !root.busy
        icon.name: "exchange-positions"
        text: root.quickValid && root.quick.label
            ? root.tr("Switch to default booking: %1", root.quick.label)
            : ""
        onTriggered: root.switchTo(root.quick, undefined, true)
    }

    PlasmaCore.Action {
        id: pickerAction
        enabled: root.hasData && !root.busy
        icon.name: "view-list-details"
        text: root.running ? root.tr("Switch with selection…") : root.tr("Start with selection…")
        onTriggered: root.openPicker()
    }

    PlasmaCore.Action {
        id: recentSeparator
        isSeparator: true
        visible: root.hasData && root.recentChoices.length > 0
    }

    Instantiator {
        id: recentActions
        model: 5
        delegate: PlasmaCore.Action {
            required property int index
            readonly property var context: root.recentChoices[index] || null
            visible: root.hasData && context !== null
            enabled: !root.busy
            icon.name: root.running ? "exchange-positions" : "media-playback-start"
            text: context ? context.label : ""
            onTriggered: root.startOrSwitch(context, true)
        }
    }

    PlasmaCore.Action {
        id: refreshSeparator
        isSeparator: true
    }

    PlasmaCore.Action {
        id: refreshAction
        text: root.tr("Refresh")
        icon.name: "view-refresh"
        onTriggered: root.refresh()
    }

    Plasmoid.contextualActions: {
        let actions = [statusAction, quickAction, switchDefaultAction, pickerAction, recentSeparator];
        for (let i = 0; i < recentActions.count; ++i) {
            actions.push(recentActions.objectAt(i));
        }
        return actions.concat([refreshSeparator, refreshAction]);
    }
}
