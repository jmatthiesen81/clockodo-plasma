// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

// Panel appearance and mouse actions.
ConfigPage {
    id: root

    property string panelStyle: "ring"
    property bool colorize: true
    property string modifier: "ctrl"
    property string modifierClick: "quick"
    property string middleClick: "quick"

    readonly property var styles: [
        { "value": "ring", "text": root.tr("Ring (default)"), "hint": root.tr("Progress towards the daily target") },
        { "value": "stopwatch", "text": root.tr("Stopwatch"), "hint": root.tr("Pause or play symbol") },
        { "value": "pill", "text": root.tr("Pill"), "hint": root.tr("Coloured time only, for narrow panels") }
    ]
    readonly property var modifiers: [
        { "value": "ctrl", "text": root.tr("Ctrl") },
        { "value": "shift", "text": root.tr("Shift") },
        { "value": "alt", "text": root.tr("Alt") },
        { "value": "meta", "text": root.tr("Meta") }
    ]
    readonly property var actions: [
        { "value": "quick", "text": root.tr("Quick start / stop") },
        { "value": "picker", "text": root.tr("Open start with selection") },
        { "value": "none", "text": root.tr("Nothing") }
    ]

    function indexOf(list, value) {
        for (let i = 0; i < list.length; ++i) {
            if (list[i].value === value) {
                return i;
            }
        }
        return 0;
    }

    edits: ({
        "panel_style": panelStyle,
        "colorize": colorize,
        "modifier": modifier,
        "modifier_click": modifierClick,
        "middle_click": middleClick
    })

    onLoaded: {
        panelStyle = settings.panel_style;
        colorize = settings.colorize;
        modifier = settings.modifier;
        modifierClick = settings.modifier_click;
        middleClick = settings.middle_click;
    }

    Kirigami.FormLayout {
        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: root.tr("Panel")
        }

        RowLayout {
            Kirigami.FormData.label: root.tr("Style:")
            spacing: Kirigami.Units.largeSpacing

            Repeater {
                model: root.styles

                QQC2.Button {
                    id: styleButton
                    required property var modelData
                    Layout.minimumWidth: Kirigami.Units.gridUnit * 7
                    padding: Kirigami.Units.largeSpacing
                    checkable: true
                    checked: root.panelStyle === modelData.value
                    onClicked: root.panelStyle = modelData.value
                    Accessible.name: modelData.text
                    Accessible.description: modelData.hint
                    QQC2.ToolTip.text: modelData.hint
                    QQC2.ToolTip.visible: hovered
                    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay

                    contentItem: ColumnLayout {
                        spacing: Kirigami.Units.smallSpacing
                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter
                            spacing: Kirigami.Units.smallSpacing
                            StatusIcon {
                                visible: styleButton.modelData.value !== "pill"
                                Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                                Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                                style: styleButton.modelData.value
                                color: Kirigami.Theme.positiveTextColor
                                running: true
                                progress: 0.6
                            }
                            Rectangle {
                                visible: styleButton.modelData.value === "pill"
                                implicitWidth: pillText.implicitWidth + Kirigami.Units.largeSpacing * 2
                                implicitHeight: pillText.implicitHeight + Kirigami.Units.smallSpacing
                                radius: height / 2
                                color: Qt.rgba(Kirigami.Theme.positiveTextColor.r, Kirigami.Theme.positiveTextColor.g,
                                               Kirigami.Theme.positiveTextColor.b, 0.16)
                                border.width: 1
                                border.color: Kirigami.Theme.positiveTextColor
                                QQC2.Label {
                                    id: pillText
                                    anchors.centerIn: parent
                                    text: "04:12"
                                    color: Kirigami.Theme.positiveTextColor
                                    font.weight: Font.DemiBold
                                }
                            }
                            QQC2.Label {
                                visible: styleButton.modelData.value !== "pill"
                                text: "04:12"
                                color: Kirigami.Theme.positiveTextColor
                                font.weight: Font.DemiBold
                            }
                        }
                        QQC2.Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: styleButton.modelData.text
                        }
                    }
                }
            }
        }

        QQC2.CheckBox {
            text: root.tr("Colour the time: running green, stopped orange")
            checked: root.colorize
            onToggled: root.colorize = checked
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: root.tr("Mouse")
        }

        QQC2.Label {
            Kirigami.FormData.label: root.tr("Left click:")
            text: root.tr("Open the popup")
        }

        RowLayout {
            Kirigami.FormData.label: root.tr("Key + left click:")
            QQC2.ComboBox {
                model: root.modifiers
                textRole: "text"
                currentIndex: root.indexOf(root.modifiers, root.modifier)
                onActivated: index => root.modifier = root.modifiers[index].value
                Accessible.name: root.tr("Key")
            }
            QQC2.Label {
                text: "→"
            }
            QQC2.ComboBox {
                model: root.actions
                textRole: "text"
                currentIndex: root.indexOf(root.actions, root.modifierClick)
                onActivated: index => root.modifierClick = root.actions[index].value
                Accessible.name: root.tr("Action for key + left click")
            }
        }

        QQC2.ComboBox {
            Kirigami.FormData.label: root.tr("Middle click:")
            model: root.actions
            textRole: "text"
            currentIndex: root.indexOf(root.actions, root.middleClick)
            onActivated: index => root.middleClick = root.actions[index].value
        }

        QQC2.Label {
            Kirigami.FormData.label: root.tr("Right click:")
            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
            wrapMode: Text.Wrap
            text: root.tr("Menu with quick start, selection and recently used bookings")
        }

        QQC2.Label {
            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
            wrapMode: Text.Wrap
            opacity: 0.7
            text: root.tr("Quick start uses the default booking; without one, the selection opens. Quick stop stops the clock shown in the panel.")
        }
    }
}
