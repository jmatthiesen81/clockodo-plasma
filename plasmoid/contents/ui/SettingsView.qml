// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami

// Global settings of the daemon (shared by all widget instances).
ColumnLayout {
    id: view

    property var settings: null
    property string message: ""
    property bool messageOk: true
    property bool showCredentials: false

    readonly property var intervals: [
        { "value": 0, "text": root.tr("Off") },
        { "value": 30, "text": root.tr("30 seconds") },
        { "value": 60, "text": root.tr("1 minute") },
        { "value": 120, "text": root.tr("2 minutes") },
        { "value": 300, "text": root.tr("5 minutes") }
    ]

    spacing: Kirigami.Units.smallSpacing

    Component.onCompleted: root.call("GetSettings", [], value => view.settings = value)

    function indexOfInterval(seconds) {
        for (let i = 0; i < intervals.length; ++i) {
            if (intervals[i].value === seconds) {
                return i;
            }
        }
        return 2;
    }

    Kirigami.FormLayout {
        Layout.fillWidth: true
        enabled: !!view.settings

        PlasmaComponents3.ComboBox {
            id: languageBox
            Kirigami.FormData.label: root.tr("Language:")
            model: view.settings ? view.settings.languages : []
            textRole: "name"
            currentIndex: {
                if (!view.settings) {
                    return 0;
                }
                const list = view.settings.languages;
                for (let i = 0; i < list.length; ++i) {
                    if (list[i].code === view.settings.language) {
                        return i;
                    }
                }
                return 0;
            }
            Accessible.name: root.tr("Language")
        }

        PlasmaComponents3.ComboBox {
            id: intervalBox
            Kirigami.FormData.label: root.tr("Update every:")
            model: view.intervals
            textRole: "text"
            currentIndex: view.settings ? view.indexOfInterval(view.settings.poll_interval) : 2
            Accessible.name: root.tr("Update interval")
        }

        PlasmaComponents3.CheckBox {
            id: lockBox
            Kirigami.FormData.label: root.tr("Reminders:")
            text: root.tr("Notify when the screen is locked while the clock runs")
            checked: view.settings ? view.settings.notify_on_lock : true
        }

        RowLayout {
            PlasmaComponents3.SpinBox {
                id: longBox
                from: 0
                to: 24
                value: view.settings ? view.settings.long_running_hours : 0
                Accessible.name: root.tr("Remind after hours of running clock")
            }
            PlasmaComponents3.Label {
                text: longBox.value === 0
                    ? root.tr("no reminder for long-running clocks")
                    : root.trp("remind after %1 hour", "remind after %1 hours", longBox.value)
            }
        }

        PlasmaComponents3.TextField {
            id: contactField
            Kirigami.FormData.label: root.tr("Contact e-mail:")
            Layout.fillWidth: true
            placeholderText: root.tr("default: your Clockodo e-mail")
            text: view.settings ? view.settings.contact_email : ""
            Accessible.name: root.tr("Contact e-mail for the Clockodo API")
        }
    }

    PlasmaComponents3.Label {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        opacity: 0.7
        text: root.tr("Clockodo requires a technical contact address for every API client.")
    }

    PlasmaComponents3.Button {
        Layout.alignment: Qt.AlignRight
        icon.name: "document-save"
        text: root.tr("Save")
        enabled: !!view.settings
        onClicked: {
            const changes = {
                "poll_interval": view.intervals[intervalBox.currentIndex].value,
                "notify_on_lock": lockBox.checked,
                "long_running_hours": longBox.value,
                "contact_email": contactField.text.trim(),
                "language": view.settings.languages[languageBox.currentIndex].code
            };
            root.call("SetSettings", [JSON.stringify(changes)], result => {
                view.messageOk = !!(result && result.ok);
                view.message = result && result.message ? result.message : "";
                // Reload: the names in the language list may have changed.
                root.call("GetSettings", [], value => view.settings = value);
            }, error => {
                view.messageOk = false;
                view.message = error;
            });
        }
    }

    Kirigami.InlineMessage {
        Layout.fillWidth: true
        visible: view.message.length > 0
        type: view.messageOk ? Kirigami.MessageType.Positive : Kirigami.MessageType.Error
        text: view.message
    }

    Kirigami.Separator {
        Layout.fillWidth: true
    }

    PlasmaComponents3.Button {
        visible: !view.showCredentials
        icon.name: "dialog-password"
        text: root.tr("Change Clockodo account or API key…")
        onClicked: view.showCredentials = true
    }

    CredentialsForm {
        Layout.fillWidth: true
        visible: view.showCredentials
        account: root.daemonState.account || ""
    }

    Item { Layout.fillHeight: true }
}
