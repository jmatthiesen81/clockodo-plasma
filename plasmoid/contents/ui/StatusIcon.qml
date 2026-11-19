// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Shapes
import org.kde.kirigami as Kirigami

// Clock state as an icon, drawn in a 24×24 grid and scaled:
//   "ring"      – progress ring towards the daily target; dot = running, square = stopped
//   "stopwatch" – stopwatch with pause bars (running) or play triangle (stopped)
// The "pill" style has no icon; CompactRepresentation draws it.
Item {
    id: icon

    property string style: "ring"
    property color color: Kirigami.Theme.textColor
    property color trackColor: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.25)
    property bool running: false
    property real progress: -1 // 0..1 of the daily target, -1 = unknown
    property bool pulse: false // gentle pulse of the dot while running (popup only)

    implicitWidth: Kirigami.Units.iconSizes.smallMedium
    implicitHeight: implicitWidth

    readonly property real unit: Math.min(width, height) / 24

    Item {
        id: grid
        width: 24
        height: 24
        anchors.centerIn: parent
        scale: icon.unit
        transformOrigin: Item.Center

        // ------------------------------------------------------------ ring
        Shape {
            anchors.fill: parent
            visible: icon.style === "ring"
            preferredRendererType: Shape.CurveRenderer

            ShapePath {
                strokeColor: icon.progress < 0 ? Qt.rgba(icon.color.r, icon.color.g, icon.color.b, 0.6) : icon.trackColor
                strokeWidth: 2.5
                fillColor: "transparent"
                PathAngleArc {
                    centerX: 12; centerY: 12; radiusX: 9; radiusY: 9
                    startAngle: 0; sweepAngle: 360
                }
            }
            ShapePath {
                strokeColor: icon.color
                strokeWidth: icon.progress > 0 ? 2.5 : 0
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: 12; centerY: 12; radiusX: 9; radiusY: 9
                    startAngle: -90
                    sweepAngle: 360 * Math.min(1, Math.max(0, icon.progress))
                }
            }
        }

        Rectangle {
            id: dot
            visible: icon.style === "ring" && icon.running
            anchors.centerIn: parent
            width: 6.5
            height: width
            radius: width / 2
            color: icon.color

            SequentialAnimation on opacity {
                running: icon.pulse && dot.visible && Kirigami.Units.longDuration > 0
                loops: Animation.Infinite
                NumberAnimation { to: 0.4; duration: 1200; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1; duration: 1200; easing.type: Easing.InOutSine }
                onRunningChanged: if (!running) dot.opacity = 1
            }
        }

        Rectangle {
            visible: icon.style === "ring" && !icon.running
            anchors.centerIn: parent
            width: 5.5
            height: width
            radius: 1
            color: icon.color
        }

        // ------------------------------------------------------------ stopwatch
        Shape {
            anchors.fill: parent
            visible: icon.style === "stopwatch"
            preferredRendererType: Shape.CurveRenderer

            ShapePath {
                strokeColor: icon.color
                strokeWidth: 2
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: 12; centerY: 13.5; radiusX: 7.5; radiusY: 7.5
                    startAngle: 0; sweepAngle: 360
                }
                PathMove { x: 10; y: 2.5 }
                PathLine { x: 14; y: 2.5 }
                PathMove { x: 12; y: 2.5 }
                PathLine { x: 12; y: 6 }
                PathMove { x: 18.5; y: 6.5 }
                PathLine { x: 20; y: 5 }
            }
            ShapePath {
                // play triangle when stopped
                strokeColor: "transparent"
                fillColor: icon.running ? "transparent" : icon.color
                startX: 10.5; startY: 10.3
                PathLine { x: 15; y: 13.5 }
                PathLine { x: 10.5; y: 16.7 }
                PathLine { x: 10.5; y: 10.3 }
            }
        }

        Row {
            visible: icon.style === "stopwatch" && icon.running
            x: 9.9
            y: 10.5
            spacing: 1.6
            Repeater {
                model: 2
                Rectangle { width: 1.7; height: 6; radius: 0.8; color: icon.color }
            }
        }
    }
}
