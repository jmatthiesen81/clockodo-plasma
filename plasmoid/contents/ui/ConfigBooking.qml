// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

// Default booking: used by the quick start and pre-selected in the popup.
ConfigPage {
    id: root

    property var contexts: null
    property string contextsError: ""
    property var selected: null
    property string text: ""

    edits: ({
        "default_customers_id": selected ? (selected.customers_id || 0) : 0,
        "default_projects_id": selected && selected.customers_id ? (selected.projects_id || 0) : 0,
        "default_services_id": selected ? (selected.services_id || 0) : 0,
        "default_text": text.trim()
    })

    onLoaded: {
        selected = settings.default_customers_id ? {
            "customers_id": settings.default_customers_id,
            "projects_id": settings.default_projects_id,
            "services_id": settings.default_services_id
        } : null;
        text = settings.default_text || "";
    }

    Component.onCompleted: root.call("ListContexts", [], value => {
        if (value && value.ok) {
            contexts = value;
        } else {
            contextsError = value ? value.message : "";
        }
    }, error => contextsError = error)

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: root.tr("Used for the quick start and pre-selected in the popup when you choose nothing else.")
        }

        ContextPicker {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 28
            enabled: !!root.contexts
            contexts: root.contexts
            selected: root.selected
            onPicked: ctx => root.selected = ctx
        }

        QQC2.Label {
            Layout.fillWidth: true
            visible: root.contextsError.length > 0
            text: root.contextsError
            wrapMode: Text.Wrap
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 28
            spacing: Kirigami.Units.smallSpacing
            QQC2.Label {
                text: root.tr("Description (optional)")
                opacity: 0.8
            }
            QQC2.TextField {
                Layout.fillWidth: true
                maximumLength: 1000
                text: root.text
                onTextEdited: root.text = text
                Accessible.name: root.tr("Description (optional)")
            }
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 28
            visible: !root.selected
            type: Kirigami.MessageType.Information
            text: root.tr("Without a default booking the quick start opens the selection.")
        }

        QQC2.Button {
            visible: !!root.selected
            icon.name: "edit-clear"
            text: root.tr("Remove default booking")
            onClicked: {
                root.selected = null;
                root.text = "";
            }
        }
    }
}
