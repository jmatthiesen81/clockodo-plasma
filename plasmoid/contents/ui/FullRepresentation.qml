// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami

PlasmaExtras.Representation {
    id: full

    Layout.minimumWidth: Kirigami.Units.gridUnit * 20
    Layout.preferredWidth: Kirigami.Units.gridUnit * 22
    Layout.minimumHeight: Kirigami.Units.gridUnit * 12
    // The header is not part of the content and must be added; the views
    // scroll if they are taller than the cap.
    Layout.preferredHeight: Math.min(
        (header ? header.implicitHeight : 0) + content.implicitHeight + Kirigami.Units.largeSpacing * 2,
        Kirigami.Units.gridUnit * 36)

    collapseMarginsHint: true

    // "main": status with quick start / stop; "picker": start or switch with selection.
    property string mode: "main"

    // Booking contexts from the daemon (ListContexts), for the picker.
    property var contexts: null
    property string contextsError: ""
    property var selected: null // {customers_id, projects_id, services_id}
    property string description: ""
    property bool rememberDefault: false

    readonly property bool needsCredentials: root.status === "unconfigured"
        || root.status === "auth_failed"
    readonly property bool switching: root.running

    readonly property string modifierName: {
        switch (root.ui.modifier) {
        case "shift": return root.tr("Shift");
        case "alt": return root.tr("Alt");
        case "meta": return root.tr("Meta");
        default: return root.tr("Ctrl");
        }
    }
    readonly property string quickHint: (root.ui.modifier_click || "quick") === "quick"
        ? root.tr("%1+click", modifierName) : ""

    function loadContexts() {
        root.call("ListContexts", [], value => {
            if (value && value.ok) {
                contexts = value;
                contextsError = "";
            } else {
                contextsError = value ? value.message : "";
            }
        }, message => contextsError = message);
    }

    function openPicker() {
        // Only pre-filled; nothing starts without an explicit click.
        if (root.quickValid) {
            selected = root.contextData(root.quick);
        } else if (root.recentChoices.length > 0) {
            selected = root.contextData(root.recentChoices[0]);
        } else {
            selected = null;
        }
        rememberDefault = false;
        mode = "picker";
        loadContexts();
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

    readonly property bool selectionComplete: !!selected && !!selected.customers_id && !!selected.services_id

    function startSelected() {
        if (!selectionComplete) {
            return;
        }
        const ctx = root.contextData(selected, description.trim());
        const remember = rememberDefault;
        root.actionMessage = "";
        const done = result => {
            root.showResult(result, false);
            if (result && result.ok) {
                description = "";
                mode = "main";
                if (remember) {
                    root.call("SetSettings", [JSON.stringify({
                        "default_customers_id": ctx.customers_id,
                        "default_projects_id": ctx.projects_id || 0,
                        "default_services_id": ctx.services_id
                    })]);
                }
            }
        };
        const failed = message => root.showError(message, false);
        if (switching && root.daemonState.running) {
            root.call("Switch", [JSON.stringify(ctx), root.daemonState.running.entry_id], done, failed);
        } else {
            root.call("Start", [JSON.stringify(ctx)], done, failed);
        }
    }

    function openSettings() {
        Plasmoid.internalAction("configure").trigger();
    }

    Connections {
        target: root
        function onExpandedChanged() {
            if (root.expanded) {
                if (full.mode !== "picker") {
                    root.actionMessage = "";
                }
            } else {
                full.mode = "main";
                full.description = "";
            }
        }
        function onPickerRequestChanged() {
            full.openPicker();
        }
    }

    Component.onCompleted: if (root.pickerRequest > 0 && root.expanded) full.openPicker()

    header: PlasmaExtras.PlasmoidHeading {
        RowLayout {
            anchors.fill: parent
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents3.ToolButton {
                visible: full.mode === "picker"
                icon.name: "go-previous"
                onClicked: full.mode = "main"
                QQC2.ToolTip.text: root.tr("Back")
                QQC2.ToolTip.visible: hovered
                Accessible.name: root.tr("Back")
            }
            Kirigami.Heading {
                Layout.fillWidth: true
                level: 3
                text: full.mode === "picker"
                    ? (full.switching ? root.tr("Switch with selection") : root.tr("Start with selection"))
                    : root.tr("Clockodo")
                elide: Text.ElideRight
            }
            PlasmaComponents3.ToolButton {
                icon.name: "view-refresh"
                enabled: !root.daemonState.syncing
                onClicked: {
                    root.refresh();
                    if (full.mode === "picker") {
                        full.loadContexts();
                    }
                }
                QQC2.ToolTip.text: root.tr("Refresh")
                QQC2.ToolTip.visible: hovered
                Accessible.name: root.tr("Refresh")
            }
            PlasmaComponents3.ToolButton {
                icon.name: "configure"
                onClicked: full.openSettings()
                QQC2.ToolTip.text: root.tr("Settings")
                QQC2.ToolTip.visible: hovered
                Accessible.name: root.tr("Settings")
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
            visible: root.actionMessage.length > 0
            type: root.actionOk ? Kirigami.MessageType.Positive : Kirigami.MessageType.Warning
            text: root.actionMessage
            showCloseButton: true
            onVisibleChanged: if (!visible) root.actionMessage = ""
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
                    if (full.needsCredentials) {
                        return credentialsView;
                    }
                    if (root.status === "secret_locked") {
                        return lockedView;
                    }
                    if (!root.hasData) {
                        return loadingView;
                    }
                    return full.mode === "picker" ? pickerView : mainView;
                }
            }
        }
    }

    // ==================================================================== main

    Component {
        id: mainView

        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            // ------------------------------------------------ status
            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.largeSpacing

                StatusIcon {
                    Layout.preferredWidth: Kirigami.Units.iconSizes.large
                    Layout.preferredHeight: Kirigami.Units.iconSizes.large
                    style: root.panelStyle === "stopwatch" ? "stopwatch" : "ring"
                    color: root.stateColor
                    running: root.running
                    progress: root.progress
                    pulse: true
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing / 2

                    Rectangle {
                        implicitWidth: stateLabel.implicitWidth + Kirigami.Units.largeSpacing
                        implicitHeight: stateLabel.implicitHeight + Kirigami.Units.smallSpacing / 2
                        radius: height / 2
                        color: Qt.rgba(root.stateColor.r, root.stateColor.g, root.stateColor.b, 0.16)

                        PlasmaComponents3.Label {
                            id: stateLabel
                            anchors.centerIn: parent
                            text: root.overtime ? root.tr("Over target")
                                : root.running ? root.tr("Running") : root.tr("Stopped")
                            color: root.stateColor
                            font.bold: true
                            font.capitalization: Font.AllUppercase
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                        }
                    }
                    PlasmaComponents3.Label {
                        Layout.fillWidth: true
                        visible: text.length > 0
                        text: {
                            if (root.running && root.daemonState.running) {
                                const since = Date.parse(root.daemonState.running.time_since);
                                const seconds = Math.max(0, Math.floor((root.nowMs - since) / 1000));
                                return root.tr("since %1 · %2 h", root.sinceText, root.formatDuration(seconds));
                            }
                            return "";
                        }
                        opacity: 0.7
                        wrapMode: Text.Wrap
                    }
                }

                ColumnLayout {
                    spacing: 0
                    PlasmaComponents3.Label {
                        Layout.alignment: Qt.AlignRight
                        text: root.totalText
                        color: root.stateColor
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 2
                        font.weight: Font.DemiBold
                        font.features: ({ "tnum": 1 })
                        Accessible.name: root.tr("Work time today: %1", root.totalText)
                    }
                    PlasmaComponents3.Label {
                        Layout.alignment: Qt.AlignRight
                        text: root.targetSeconds > 0
                            ? root.tr("today · target %1", root.formatDuration(root.targetSeconds))
                            : root.tr("today")
                        opacity: 0.7
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                    }
                }
            }

            // Progress towards the daily target.
            Rectangle {
                Layout.fillWidth: true
                visible: root.targetSeconds > 0
                implicitHeight: Math.round(Kirigami.Units.smallSpacing * 1.5)
                radius: height / 2
                color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.15)

                Rectangle {
                    width: parent.width * Math.min(1, Math.max(0, root.progress))
                    height: parent.height
                    radius: parent.radius
                    color: root.stateColor
                }
            }

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: root.stale && !!root.daemonState.last_sync
                text: root.tr("Outdated – last update %1", root.formatTime(root.daemonState.last_sync))
                font.italic: true
                wrapMode: Text.Wrap
            }

            // ------------------------------------------------ stopped: quick start
            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.running
                spacing: Kirigami.Units.smallSpacing

                SectionLabel { text: root.tr("Default booking") }

                PlasmaComponents3.Button {
                    Layout.fillWidth: true
                    visible: root.quickValid
                    enabled: !root.busy && !root.stale
                    onClicked: root.startContext(root.quick, full.description.trim() || root.quick.text, false)
                    Accessible.name: root.tr("Quick start: %1", root.quick ? root.quick.label : "")

                    contentItem: RowLayout {
                        spacing: Kirigami.Units.largeSpacing
                        Kirigami.Icon {
                            Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                            Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                            source: "media-playback-start"
                            color: Kirigami.Theme.positiveTextColor
                            isMask: true
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            PlasmaComponents3.Label {
                                text: root.tr("Quick start")
                                font.bold: true
                            }
                            PlasmaComponents3.Label {
                                Layout.fillWidth: true
                                text: root.quick ? (root.quick.label || "") : ""
                                wrapMode: Text.Wrap
                                opacity: 0.8
                            }
                        }
                        PlasmaComponents3.Label {
                            visible: full.quickHint.length > 0
                            text: full.quickHint
                            opacity: 0.6
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                        }
                    }
                }

                PlasmaComponents3.Label {
                    Layout.fillWidth: true
                    visible: !root.quickValid
                    wrapMode: Text.Wrap
                    opacity: 0.8
                    text: root.quick
                        ? root.tr("The default booking is no longer active. Please choose a new one.")
                        : root.tr("No default booking yet. With one, a click starts the clock right away.")
                }
                PlasmaComponents3.Button {
                    visible: !root.quickValid
                    icon.name: "configure"
                    text: root.tr("Set default booking…")
                    onClicked: full.openSettings()
                }

                PlasmaComponents3.TextField {
                    Layout.fillWidth: true
                    visible: root.quickValid
                    placeholderText: root.quick && root.quick.text
                        ? root.quick.text : root.tr("Description (optional)")
                    maximumLength: 1000
                    text: full.description
                    onTextEdited: full.description = text
                    onAccepted: if (root.quickValid) root.startContext(root.quick, full.description.trim() || root.quick.text, false)
                    Accessible.name: root.tr("Description (optional)")
                }
            }

            // ------------------------------------------------ running: booked on, stop, switch
            ColumnLayout {
                Layout.fillWidth: true
                visible: root.running && !!root.daemonState.running
                spacing: Kirigami.Units.smallSpacing

                SectionLabel { text: root.tr("Booked on") }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: bookedColumn.implicitHeight + Kirigami.Units.largeSpacing * 2
                    radius: Kirigami.Units.cornerRadius
                    color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.07)

                    ColumnLayout {
                        id: bookedColumn
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.largeSpacing
                        spacing: Kirigami.Units.smallSpacing / 2

                        Repeater {
                            model: root.daemonState.running ? root.daemonState.running.label.split(" › ") : []
                            PlasmaComponents3.Label {
                                required property string modelData
                                required property int index
                                Layout.fillWidth: true
                                text: modelData
                                font.bold: index === 0
                                wrapMode: Text.Wrap
                            }
                        }
                        PlasmaComponents3.Label {
                            Layout.fillWidth: true
                            visible: !!root.daemonState.running && !!root.daemonState.running.text
                            text: root.daemonState.running && root.daemonState.running.text
                                ? "„" + root.daemonState.running.text + "“" : ""
                            font.italic: true
                            opacity: 0.8
                            wrapMode: Text.Wrap
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    PlasmaComponents3.Button {
                        Layout.fillWidth: true
                        icon.name: "media-playback-stop"
                        text: root.tr("Stop")
                        enabled: !root.busy && !root.stale
                        onClicked: {
                            root.actionMessage = "";
                            root.call("Stop", [root.daemonState.running.entry_id],
                                      result => root.showResult(result, false),
                                      message => root.showError(message, false));
                        }
                    }
                    PlasmaComponents3.Button {
                        icon.name: "exchange-positions"
                        text: root.tr("Switch…")
                        enabled: !root.busy && !root.stale
                        onClicked: full.openPicker()
                    }
                }
            }

            // ------------------------------------------------ shortcuts
            ColumnLayout {
                id: shortcuts
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing / 2
                readonly property var targets: {
                    let list = [];
                    if (root.running && root.quickValid && !root.sameContext(root.quick, root.daemonState.running)) {
                        list.push(root.quick);
                    }
                    for (const ctx of root.recentChoices) {
                        if (!list.some(x => root.sameContext(x, ctx))
                                && !(!root.running && root.sameContext(ctx, root.quick))) {
                            list.push(ctx);
                        }
                    }
                    return list;
                }
                visible: targets.length > 0

                SectionLabel {
                    Layout.topMargin: Kirigami.Units.smallSpacing
                    text: root.running ? root.tr("Switch directly to") : root.tr("Recently used")
                }
                Repeater {
                    model: shortcuts.targets
                    PlasmaComponents3.ItemDelegate {
                        required property var modelData
                        Layout.fillWidth: true
                        icon.name: root.running ? "exchange-positions" : "media-playback-start"
                        text: modelData.label || ""
                        enabled: !root.busy && !root.stale
                        onClicked: root.running
                            ? root.switchTo(modelData, undefined, false)
                            : root.startContext(modelData, full.description.trim() || undefined, false)
                    }
                }
            }

            PlasmaComponents3.Button {
                Layout.fillWidth: true
                visible: !root.running
                icon.name: "view-list-details"
                text: root.tr("Start with selection…")
                enabled: !root.busy
                onClicked: full.openPicker()
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

    // ==================================================================== picker

    Component {
        id: pickerView

        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            ContextPicker {
                Layout.fillWidth: true
                contexts: full.contexts
                selected: full.selected
                onPicked: ctx => full.selected = ctx
            }

            PlasmaComponents3.Label {
                Layout.fillWidth: true
                visible: full.contextsError.length > 0
                text: full.contextsError
                wrapMode: Text.Wrap
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                PlasmaComponents3.Label {
                    text: root.tr("Description (optional)")
                    opacity: 0.8
                }
                PlasmaComponents3.TextField {
                    Layout.fillWidth: true
                    maximumLength: 1000
                    text: full.description
                    onTextEdited: full.description = text
                    onAccepted: full.startSelected()
                    Accessible.name: root.tr("Description (optional)")
                }
            }

            // The selected context is shown in full right above the start button.
            Kirigami.Heading {
                Layout.fillWidth: true
                level: 4
                wrapMode: Text.Wrap
                text: full.selectionComplete ? root.tr("Book on: %1", full.labelOf(full.selected))
                                             : root.tr("Please choose customer and service.")
            }

            PlasmaComponents3.CheckBox {
                Layout.fillWidth: true
                text: root.tr("Remember as default booking")
                checked: full.rememberDefault
                onToggled: full.rememberDefault = checked
            }

            RowLayout {
                Layout.fillWidth: true
                PlasmaComponents3.Button {
                    Layout.fillWidth: true
                    icon.name: full.switching ? "exchange-positions" : "media-playback-start"
                    text: full.switching ? root.tr("Switch to this") : root.tr("Start")
                    enabled: !root.busy && !root.stale && full.selectionComplete
                    onClicked: full.startSelected()
                }
                PlasmaComponents3.Button {
                    text: root.tr("Cancel")
                    onClicked: full.mode = "main"
                }
            }

            PlasmaComponents3.BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                visible: root.busy
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
                onClicked: root.call("Unlock", [], result => root.showResult(result, false),
                                     message => root.showError(message, false))
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
}
