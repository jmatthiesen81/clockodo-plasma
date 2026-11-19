// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami

// Panel: state icon and today's total in the chosen style (ring, stopwatch,
// pill). Left click opens the popup; modifier + left click and middle click
// run the configured action (quick start/stop or the picker).
MouseArea {
    id: compact

    readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical
    readonly property bool pill: root.panelStyle === "pill"
    readonly property bool problem: root.status === "auth_failed" || root.status === "secret_locked"
        || root.status === "unconfigured" || !root.daemonReachable

    readonly property int modifierFlag: {
        switch (root.ui.modifier) {
        case "shift": return Qt.ShiftModifier;
        case "alt": return Qt.AltModifier;
        case "meta": return Qt.MetaModifier;
        default: return Qt.ControlModifier;
        }
    }

    Layout.minimumWidth: vertical ? -1 : content.implicitWidth + Kirigami.Units.smallSpacing * 2
    Layout.minimumHeight: vertical ? content.implicitHeight : -1

    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.MiddleButton
    onClicked: mouse => {
        if (mouse.button === Qt.MiddleButton) {
            root.runClickAction(root.ui.middle_click || "quick");
        } else if (mouse.modifiers & compact.modifierFlag) {
            root.runClickAction(root.ui.modifier_click || "quick");
        } else {
            root.expanded = !root.expanded;
        }
    }

    Accessible.role: Accessible.Button
    Accessible.name: root.toolTipMainText
    Accessible.description: root.toolTipSubText
    Accessible.onPressAction: root.expanded = !root.expanded

    Item {
        id: content
        anchors.centerIn: parent
        implicitWidth: compact.pill ? pillBox.implicitWidth : row.implicitWidth
        implicitHeight: compact.pill ? pillBox.implicitHeight : row.implicitHeight
        width: implicitWidth
        height: implicitHeight
        opacity: root.stale ? 0.6 : 1

        // ------------------------------------------------ ring / stopwatch
        RowLayout {
            id: row
            visible: !compact.pill
            anchors.centerIn: parent
            spacing: Kirigami.Units.smallSpacing

            StatusIcon {
                Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                style: root.panelStyle
                color: root.panelColor
                running: root.running
                progress: root.progress
            }

            PlasmaComponents3.Label {
                text: root.totalText
                color: root.panelColor
                font.weight: Font.DemiBold
                font.features: ({ "tnum": 1 })
                // Stale data is also marked in text, not only by opacity.
                font.italic: root.stale
            }

            Kirigami.Icon {
                visible: compact.problem
                Layout.preferredWidth: Kirigami.Units.iconSizes.small
                Layout.preferredHeight: Kirigami.Units.iconSizes.small
                source: "dialog-warning"
            }
        }

        // ------------------------------------------------ pill
        Rectangle {
            id: pillBox
            visible: compact.pill
            anchors.centerIn: parent
            implicitWidth: pillRow.implicitWidth + Kirigami.Units.smallSpacing * 3
            implicitHeight: pillRow.implicitHeight + Kirigami.Units.smallSpacing
            radius: height / 2
            color: Qt.rgba(root.panelColor.r, root.panelColor.g, root.panelColor.b, 0.16)
            border.width: 1
            border.color: root.panelColor

            RowLayout {
                id: pillRow
                anchors.centerIn: parent
                spacing: Kirigami.Units.smallSpacing

                Rectangle {
                    Layout.preferredWidth: Math.round(Kirigami.Units.gridUnit * 0.45)
                    Layout.preferredHeight: Layout.preferredWidth
                    radius: root.running ? width / 2 : 2
                    color: root.panelColor
                }
                PlasmaComponents3.Label {
                    text: root.totalText
                    color: root.panelColor
                    font.weight: Font.DemiBold
                    font.features: ({ "tnum": 1 })
                    font.italic: root.stale
                }
                Kirigami.Icon {
                    visible: compact.problem
                    Layout.preferredWidth: Kirigami.Units.iconSizes.small
                    Layout.preferredHeight: Kirigami.Units.iconSizes.small
                    source: "dialog-warning"
                }
            }
        }
    }
}
