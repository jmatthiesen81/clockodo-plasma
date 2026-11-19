// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami

MouseArea {
    id: compact

    readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical

    Layout.minimumWidth: vertical ? -1 : row.implicitWidth + Kirigami.Units.smallSpacing * 2
    Layout.minimumHeight: vertical ? row.implicitHeight : -1

    hoverEnabled: true
    acceptedButtons: Qt.LeftButton
    onClicked: root.expanded = !root.expanded

    Accessible.role: Accessible.Button
    Accessible.name: root.toolTipMainText
    Accessible.description: root.toolTipSubText
    Accessible.onPressAction: root.expanded = !root.expanded

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Icon {
            Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
            Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
            source: root.running ? "media-playback-pause" : "media-playback-start"
            active: compact.containsMouse
            opacity: root.stale ? 0.5 : 1
        }

        PlasmaComponents3.Label {
            text: root.totalText
            font.features: ({ "tnum": 1 })
            opacity: root.stale ? 0.6 : 1
            // Stale data is also marked in text, not only by opacity.
            font.italic: root.stale
        }

        Kirigami.Icon {
            visible: root.status === "auth_failed" || root.status === "secret_locked"
                || root.status === "unconfigured" || !root.daemonReachable
            Layout.preferredWidth: Kirigami.Units.iconSizes.small
            Layout.preferredHeight: Kirigami.Units.iconSizes.small
            source: "dialog-warning"
        }
    }
}
