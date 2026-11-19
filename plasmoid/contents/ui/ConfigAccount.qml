// SPDX-License-Identifier: MPL-2.0
import QtQuick

// Clockodo account and API key. The form checks and saves on its own button;
// nothing here is saved with the dialog's Apply.
ConfigPage {
    id: root

    property string account: ""

    Component.onCompleted: root.call("GetState", [], value => {
        if (value && typeof value === "object") {
            account = value.account || "";
        }
    })

    CredentialsForm {
        width: parent ? parent.width : implicitWidth
        account: root.account
    }
}
