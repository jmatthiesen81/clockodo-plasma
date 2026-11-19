// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

// Daily target and reminders.
ConfigPage {
    id: root

    property bool overtimeColor: true
    property bool overtimeNotify: true
    property int overtimeAfter: 0
    property int overtimeRepeat: 60
    property bool notifyOnLock: true
    property int longRunningHours: 0

    edits: ({
        "overtime_color": overtimeColor,
        "overtime_notify": overtimeNotify,
        "overtime_after_minutes": overtimeAfter,
        "overtime_repeat_minutes": overtimeRepeat,
        "notify_on_lock": notifyOnLock,
        "long_running_hours": longRunningHours
    })

    onLoaded: {
        overtimeColor = settings.overtime_color;
        overtimeNotify = settings.overtime_notify;
        overtimeAfter = settings.overtime_after_minutes;
        overtimeRepeat = settings.overtime_repeat_minutes;
        notifyOnLock = settings.notify_on_lock;
        longRunningHours = settings.long_running_hours;
    }

    Kirigami.FormLayout {
        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: root.tr("Daily target")
        }

        QQC2.CheckBox {
            text: root.tr("Colour red when the daily target is exceeded")
            checked: root.overtimeColor
            onToggled: root.overtimeColor = checked
        }

        QQC2.CheckBox {
            text: root.tr("Notify when the daily target is exceeded")
            checked: root.overtimeNotify
            onToggled: root.overtimeNotify = checked
        }

        RowLayout {
            Kirigami.FormData.label: root.tr("First warning:")
            enabled: root.overtimeNotify
            QQC2.SpinBox {
                from: 0
                to: 240
                stepSize: 15
                value: root.overtimeAfter
                onValueModified: root.overtimeAfter = value
                Accessible.name: root.tr("Minutes over target before the first warning")
            }
            QQC2.Label {
                text: root.overtimeAfter === 0
                    ? root.tr("right when the target is reached")
                    : root.trp("%1 minute over target", "%1 minutes over target", root.overtimeAfter)
            }
        }

        RowLayout {
            Kirigami.FormData.label: root.tr("Repeat:")
            enabled: root.overtimeNotify
            QQC2.SpinBox {
                from: 0
                to: 480
                stepSize: 15
                value: root.overtimeRepeat
                onValueModified: root.overtimeRepeat = value
                Accessible.name: root.tr("Minutes between warnings")
            }
            QQC2.Label {
                text: root.overtimeRepeat === 0
                    ? root.tr("only once per day")
                    : root.trp("every %1 minute", "every %1 minutes", root.overtimeRepeat)
            }
        }

        QQC2.Label {
            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
            wrapMode: Text.Wrap
            opacity: 0.7
            text: root.tr("The target comes from your target hours in Clockodo, including public holidays and absences. Without target hours there is no colouring and no warning.")
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: root.tr("Running clock")
        }

        QQC2.CheckBox {
            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
            text: root.tr("Notify when the screen is locked while the clock runs")
            checked: root.notifyOnLock
            onToggled: root.notifyOnLock = checked
        }

        RowLayout {
            Kirigami.FormData.label: root.tr("Long-running clock:")
            QQC2.SpinBox {
                from: 0
                to: 24
                value: root.longRunningHours
                onValueModified: root.longRunningHours = value
                Accessible.name: root.tr("Remind after hours of running clock")
            }
            QQC2.Label {
                text: root.longRunningHours === 0
                    ? root.tr("no reminder for long-running clocks")
                    : root.trp("remind after %1 hour", "remind after %1 hours", root.longRunningHours)
            }
        }
    }
}
