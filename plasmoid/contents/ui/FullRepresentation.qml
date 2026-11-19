// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami

PlasmaExtras.Representation {
    id: full

    Layout.minimumWidth: Kirigami.Units.gridUnit * 20
    Layout.preferredWidth: Kirigami.Units.gridUnit * 24
    Layout.minimumHeight: Kirigami.Units.gridUnit * 16
    // The header is not part of the content and must be added; the views
    // scroll if they are taller than the cap.
    Layout.preferredHeight: Math.min(
        (header ? header.implicitHeight : 0) + content.implicitHeight + Kirigami.Units.largeSpacing * 2,
        Kirigami.Units.gridUnit * 36)

    collapseMarginsHint: true

    property bool showSettings: false
    property bool switching: false
    property string actionMessage: ""
    property bool actionOk: true

    // Booking contexts from the daemon (ListContexts).
    property var contexts: null
    property string contextsError: ""
    property var selected: null // {customers_id, projects_id, services_id}
    property string description: ""

    readonly property bool needsCredentials: root.status === "unconfigured"
        || root.status === "auth_failed"

    function loadContexts() {
        root.call("ListContexts", [], value => {
            if (value && value.ok) {
                contexts = value;
                contextsError = "";
                if (!selected && value.recent.length > 0) {
                    // Only pre-filled; never started without an explicit click.
                    selected = value.recent[0];
                }
            } else {
                contextsError = value ? value.message : "";
            }
        }, message => contextsError = message);
    }

    function nameOf(list, id) {
        if (!contexts || !id) {
            return "";
        }
        const item = contexts[list].find(x => x.id === id);
        return item ? item.name : "#" + id;
    }

    function labelOf(ctx) {
        if (!ctx) {
            return "";
        }
        let parts = [nameOf("customers", ctx.customers_id)];
        if (ctx.projects_id) {
            parts.push(nameOf("projects", ctx.projects_id));
        }
        parts.push(nameOf("services", ctx.services_id));
        return parts.join(" › ");
    }

    function showResult(result) {
        actionOk = !!(result && result.ok);
        actionMessage = result && result.message ? result.message : "";
    }

    function startClock() {
        if (!selected || !selected.customers_id || !selected.services_id) {
            return;
        }
        const ctx = {
            "customers_id": selected.customers_id,
            "projects_id": selected.projects_id || null,
            "services_id": selected.services_id,
            "text": description.trim() || null
        };
        actionMessage = "";
        if (switching && root.daemonState.running) {
            root.call("Switch", [JSON.stringify(ctx), root.daemonState.running.entry_id], result => {
                showResult(result);
                if (result && result.ok) {
                    switching = false;
                    description = "";
                }
            }, message => showResult({ "ok": false, "message": message }));
        } else {
            root.call("Start", [JSON.stringify(ctx)], result => {
                showResult(result);
                if (result && result.ok) {
                    description = "";
                }
            }, message => showResult({ "ok": false, "message": message }));
        }
    }

    function stopClock() {
        if (!root.daemonState.running) {
            return;
        }
        actionMessage = "";
        root.call("Stop", [root.daemonState.running.entry_id], showResult,
                  message => showResult({ "ok": false, "message": message }));
    }

    Connections {
        target: root
        function onExpandedChanged() {
            if (root.expanded) {
                full.actionMessage = "";
                if (root.hasData) {
                    full.loadContexts();
                }
            } else {
                full.switching = false;
                full.showSettings = false;
            }
        }
        function onStatusChanged() {
            if (root.hasData && !full.contexts) {
                full.loadContexts();
            }
        }
    }

    header: PlasmaExtras.PlasmoidHeading {
        RowLayout {
            anchors.fill: parent
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Heading {
                Layout.fillWidth: true
                level: 3
                text: full.showSettings ? root.tr("Settings") : root.tr("Clockodo")
                elide: Text.ElideRight
            }
            PlasmaComponents3.ToolButton {
                icon.name: "view-refresh"
                enabled: !root.daemonState.syncing
                onClicked: {
                    root.refresh();
                    if (root.hasData) {
                        full.loadContexts();
                    }
                }
                QQC2.ToolTip.text: root.tr("Refresh")
                QQC2.ToolTip.visible: hovered
                Accessible.name: root.tr("Refresh")
            }
            PlasmaComponents3.ToolButton {
                icon.name: full.showSettings ? "go-previous" : "configure"
                checkable: true
                checked: full.showSettings
                onToggled: full.showSettings = checked
                QQC2.ToolTip.text: full.showSettings ? root.tr("Back") : root.tr("Settings")
                QQC2.ToolTip.visible: hovered
                Accessible.name: full.showSettings ? root.tr("Back") : root.tr("Settings")
            }
        }
    }

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: Kirigami.Units.largeSpacing
        spacing: Kirigami.Units.largeSpacing

        // ---------------------------------------------------------------- messages

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !root.daemonReachable
            type: Kirigami.MessageType.Error
            text: root.tr("The background service is not reachable. Check \"systemctl --user status clockodo-plasma\".")
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: root.daemonReachable && !!root.daemonState.error
            type: root.status === "auth_failed" || root.status === "secret_locked"
                ? Kirigami.MessageType.Error : Kirigami.MessageType.Warning
            text: root.daemonState.error || ""
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: full.actionMessage.length > 0
            type: full.actionOk ? Kirigami.MessageType.Positive : Kirigami.MessageType.Warning
            text: full.actionMessage
            showCloseButton: true
            onVisibleChanged: if (!visible) full.actionMessage = ""
        }

        Kirigami.InlineMessage {
            id: noticeMessage
            property int seenId: 0
            Layout.fillWidth: true
            visible: !!root.daemonState.notice && root.daemonState.notice_id !== seenId
            type: Kirigami.MessageType.Information
            text: root.daemonState.notice || ""
            showCloseButton: true
            onVisibleChanged: if (!visible) seenId = root.daemonState.notice_id
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !!root.daemonState.timezone_mismatch
            type: Kirigami.MessageType.Information
            text: root.tr("Your Clockodo time zone (%1) differs from this computer's. \"Today\" follows Clockodo.",
                       root.daemonState.timezone || "")
        }

        // ---------------------------------------------------------------- views

        // Views scroll vertically only; their width is bound to the popup so
        // long texts wrap instead of being cut off on the right.
        PlasmaComponents3.ScrollView {
            id: viewScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            implicitHeight: viewLoader.implicitHeight
            contentWidth: availableWidth
            contentHeight: viewLoader.implicitHeight
            QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff

            Loader {
                id: viewLoader
                width: viewScroll.availableWidth
                height: Math.max(implicitHeight, viewScroll.availableHeight)
                sourceComponent: {
                    if (full.showSettings) {
                        return settingsView;
                    }
                    if (full.needsCredentials) {
                        return credentialsView;
                    }
                    if (root.status === "secret_locked") {
                        return lockedView;
                    }
                    if (!root.hasData) {
                        return loadingView;
                    }
                    return trackingView;
                }
            }
        }
    }

    // ==================================================================== tracking

    Component {
        id: trackingView

        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            RowLayout {
                Layout.fillWidth: true
                Kirigami.Icon {
                    Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                    source: root.running ? "media-playback-pause" : "media-playback-start"
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    PlasmaComponents3.Label {
                        text: root.running ? root.tr("Clock is running") : root.tr("Clock is stopped")
                        font.bold: true
                    }
                    PlasmaComponents3.Label {
                        Layout.fillWidth: true
                        visible: root.running && !!root.daemonState.running
                        text: root.daemonState.running
                            ? root.tr("%1 – since %2", root.daemonState.running.label,
                                   root.formatTime(root.daemonState.running.time_since))
                            : ""
                        wrapMode: Text.Wrap
                    }
                }
                ColumnLayout {
                    spacing: 0
                    PlasmaComponents3.Label {
                        Layout.alignment: Qt.AlignRight
                        text: root.totalText
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.6
                        font.features: ({ "tnum": 1 })
                        Accessible.name: root.tr("Work time today: %1", root.totalText)
                    }
                    PlasmaComponents3.Label {
                        Layout.alignment: Qt.AlignRight
                        text: root.tr("today")
                        opacity: 0.7
                    }
                }
            }

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: root.stale && !!root.daemonState.last_sync
                text: root.tr("Outdated – last update %1", root.formatTime(root.daemonState.last_sync))
                font.italic: true
                wrapMode: Text.Wrap
            }

            // Running: stop or switch.
            RowLayout {
                Layout.fillWidth: true
                visible: root.running && !full.switching
                PlasmaComponents3.Button {
                    Layout.fillWidth: true
                    icon.name: "media-playback-stop"
                    text: root.tr("Stop")
                    enabled: !root.busy && !root.stale
                    onClicked: full.stopClock()
                }
                PlasmaComponents3.Button {
                    icon.name: "exchange-positions"
                    text: root.tr("Switch…")
                    enabled: !root.busy && !root.stale
                    onClicked: {
                        full.switching = true;
                        full.loadContexts();
                    }
                }
            }

            // Stopped (or switching): choose the context explicitly, then start.
            ContextPicker {
                id: picker
                Layout.fillWidth: true
                visible: !root.running || full.switching
                contexts: full.contexts
                selected: full.selected
                onPicked: ctx => full.selected = ctx
            }

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: picker.visible && full.contextsError.length > 0
                text: full.contextsError
                wrapMode: Text.Wrap
            }

            PlasmaComponents3.TextField {
                id: descriptionField
                Layout.fillWidth: true
                visible: picker.visible
                placeholderText: root.tr("Description (optional)")
                maximumLength: 1000
                text: full.description
                onTextEdited: full.description = text
            }

            // The selected context is shown in full right above the start button.
            Kirigami.Heading {
                Layout.fillWidth: true
                visible: picker.visible
                level: 4
                wrapMode: Text.Wrap
                text: full.selected ? root.tr("Book on: %1", full.labelOf(full.selected))
                                    : root.tr("Please choose customer and service.")
            }

            RowLayout {
                Layout.fillWidth: true
                visible: picker.visible
                PlasmaComponents3.Button {
                    Layout.fillWidth: true
                    icon.name: "media-playback-start"
                    text: full.switching ? root.tr("Switch to this") : root.tr("Start")
                    enabled: !root.busy && !root.stale && !!full.selected
                        && !!full.selected.customers_id && !!full.selected.services_id
                    onClicked: full.startClock()
                }
                PlasmaComponents3.Button {
                    visible: full.switching
                    text: root.tr("Cancel")
                    onClicked: full.switching = false
                }
            }

            PlasmaComponents3.BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                visible: root.busy || !!root.daemonState.syncing
                running: visible
                implicitHeight: Kirigami.Units.iconSizes.medium
            }

            Item { Layout.fillHeight: true }
        }
    }

    // ==================================================================== credentials

    Component {
        id: credentialsView
        CredentialsForm {
            account: root.daemonState.account || ""
        }
    }

    // ==================================================================== locked wallet

    Component {
        id: lockedView
        ColumnLayout {
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                text: root.tr("Your Clockodo credentials are stored in the wallet, which is locked.")
                wrapMode: Text.Wrap
            }
            PlasmaComponents3.Button {
                icon.name: "unlock"
                text: root.tr("Unlock")
                onClicked: root.call("Unlock", [], full.showResult,
                                     message => full.showResult({ "ok": false, "message": message }))
            }
            Item { Layout.fillHeight: true }
        }
    }

    Component {
        id: loadingView
        ColumnLayout {
            PlasmaComponents3.BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: root.daemonReachable
                visible: running
            }
            PlasmaComponents3.Label {
                Layout.alignment: Qt.AlignHCenter
                text: root.tr("Connecting to Clockodo…")
                visible: root.daemonReachable
            }
            Item { Layout.fillHeight: true }
        }
    }

    // ==================================================================== settings

    Component {
        id: settingsView
        SettingsView {}
    }
}
