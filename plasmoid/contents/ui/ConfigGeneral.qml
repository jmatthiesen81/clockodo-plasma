// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

// Language, update interval and the contact address for the Clockodo API.
ConfigPage {
    id: root

    property string language: "system"
    property int pollInterval: 60
    property string contactEmail: ""

    readonly property var intervals: [
        { "value": 0, "text": root.tr("Off") },
        { "value": 30, "text": root.tr("30 seconds") },
        { "value": 60, "text": root.tr("1 minute") },
        { "value": 120, "text": root.tr("2 minutes") },
        { "value": 300, "text": root.tr("5 minutes") }
    ]
    readonly property var languages: settings ? settings.languages : []

    function indexOf(list, key, value) {
        for (let i = 0; i < list.length; ++i) {
            if (list[i][key] === value) {
                return i;
            }
        }
        return 0;
    }

    edits: ({
        "language": language,
        "poll_interval": pollInterval,
        "contact_email": contactEmail.trim()
    })

    onLoaded: {
        language = settings.language;
        pollInterval = settings.poll_interval;
        contactEmail = settings.contact_email;
    }

    Kirigami.FormLayout {
        QQC2.ComboBox {
            Kirigami.FormData.label: root.tr("Language:")
            model: root.languages
            textRole: "name"
            currentIndex: root.indexOf(root.languages, "code", root.language)
            onActivated: index => root.language = root.languages[index].code
            Accessible.name: root.tr("Language")
        }

        QQC2.ComboBox {
            Kirigami.FormData.label: root.tr("Update every:")
            model: root.intervals
            textRole: "text"
            currentIndex: root.indexOf(root.intervals, "value", root.pollInterval)
            onActivated: index => root.pollInterval = root.intervals[index].value
            Accessible.name: root.tr("Update interval")
        }

        QQC2.TextField {
            Kirigami.FormData.label: root.tr("Contact e-mail:")
            Layout.preferredWidth: Kirigami.Units.gridUnit * 16
            placeholderText: root.tr("default: your Clockodo e-mail")
            text: root.contactEmail
            onTextEdited: root.contactEmail = text
            Accessible.name: root.tr("Contact e-mail for the Clockodo API")
        }

        QQC2.Label {
            Layout.maximumWidth: Kirigami.Units.gridUnit * 22
            wrapMode: Text.Wrap
            opacity: 0.7
            text: root.tr("Clockodo requires a technical contact address for every API client.")
        }
    }
}
