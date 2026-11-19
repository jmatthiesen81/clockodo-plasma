// SPDX-License-Identifier: MPL-2.0
import QtQuick
import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami

// Base of the configuration pages. The settings belong to the daemon (shared
// by all widget instances), so a page loads them with GetSettings and saves
// its edits with SetSettings when the dialog's Apply/OK is pressed: Plasma's
// configuration dialog calls saveConfig() and watches unsavedChanges.
//
// A page binds `edits` to {setting: value} of its controls and sets its
// controls from `settings` in onLoaded.
KCM.SimpleKCM {
    id: page

    property var settings: null
    property var edits: ({})
    property string message: ""
    property bool messageOk: true

    readonly property bool unsavedChanges: {
        if (!settings) {
            return false;
        }
        for (const key in edits) {
            if (edits[key] !== settings[key]) {
                return true;
            }
        }
        return false;
    }

    signal loaded()

    function tr(text, arg1, arg2) {
        return daemon.tr(text, arg1, arg2);
    }

    function trp(singular, plural, n) {
        return daemon.trp(singular, plural, n);
    }

    function call(member, args, onDone, onError) {
        daemon.call(member, args, onDone, onError);
    }

    function load() {
        call("GetSettings", [], value => {
            if (typeof value !== "object") {
                return;
            }
            daemon.language = value.language_effective || daemon.systemLanguage();
            settings = value;
            loaded();
        }, error => {
            messageOk = false;
            message = tr("The background service is not reachable. Check \"systemctl --user status clockodo-plasma\".");
        });
    }

    function saveConfig() {
        if (!unsavedChanges) {
            return;
        }
        call("SetSettings", [JSON.stringify(edits)], result => {
            messageOk = !!(result && result.ok);
            message = messageOk ? "" : (result && result.message ? result.message : "");
            load();
        }, error => {
            messageOk = false;
            message = error;
        });
    }

    Component.onCompleted: load()

    DaemonClient {
        id: daemon
    }

    header: Kirigami.InlineMessage {
        visible: page.message.length > 0
        position: Kirigami.InlineMessage.Position.Header
        type: page.messageOk ? Kirigami.MessageType.Positive : Kirigami.MessageType.Error
        text: page.message
        showCloseButton: true
        onVisibleChanged: if (!visible) page.message = ""
    }
}
