// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami

// E-mail and API key; the daemon verifies them with Clockodo and stores them
// in the Secret Service (KWallet). The key never leaves this form otherwise.
ColumnLayout {
    id: form

    property string account: ""
    property bool working: false
    property string message: ""
    property bool messageOk: false

    spacing: Kirigami.Units.smallSpacing

    PlasmaComponents3.Label {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: root.tr("Enter your Clockodo e-mail address and API key. You find the key in Clockodo under \"Personal data\". The key grants the same access as your password and is stored in the wallet.")
    }

    Kirigami.FormLayout {
        Layout.fillWidth: true

        PlasmaComponents3.TextField {
            id: emailField
            Kirigami.FormData.label: root.tr("E-mail:")
            Layout.fillWidth: true
            text: form.account
            inputMethodHints: Qt.ImhEmailCharactersOnly | Qt.ImhNoAutoUppercase
            Accessible.name: root.tr("E-mail")
        }

        PlasmaComponents3.TextField {
            id: keyField
            Kirigami.FormData.label: root.tr("API key:")
            Layout.fillWidth: true
            echoMode: TextInput.Password
            inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
            Accessible.name: root.tr("API key")
            onAccepted: saveButton.clicked()
        }
    }

    PlasmaComponents3.Button {
        id: saveButton
        Layout.alignment: Qt.AlignRight
        icon.name: "document-save"
        text: root.tr("Check and save")
        enabled: !form.working && emailField.text.trim().length > 0 && keyField.text.trim().length > 0
        onClicked: {
            form.working = true;
            form.message = "";
            root.call("SetCredentials", [emailField.text.trim(), keyField.text.trim()], result => {
                form.working = false;
                form.messageOk = !!(result && result.ok);
                form.message = result && result.message ? result.message : "";
                if (form.messageOk) {
                    keyField.text = "";
                }
            }, error => {
                form.working = false;
                form.messageOk = false;
                form.message = error;
            });
        }
    }

    PlasmaComponents3.BusyIndicator {
        Layout.alignment: Qt.AlignHCenter
        visible: form.working
        running: visible
    }

    Kirigami.InlineMessage {
        Layout.fillWidth: true
        visible: form.message.length > 0
        type: form.messageOk ? Kirigami.MessageType.Positive : Kirigami.MessageType.Error
        text: form.message
    }

    Item { Layout.fillHeight: true }
}
