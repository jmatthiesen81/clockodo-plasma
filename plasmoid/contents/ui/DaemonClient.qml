// SPDX-License-Identifier: MPL-2.0
import QtQuick
import org.kde.plasma.workspace.dbus as DBus
import "translations.js" as Translations

// Calls to the background daemon and the widget's translations. Used by the
// popup (main.qml) and by the configuration pages, which run in their own
// window and cannot reach main.qml.
QtObject {
    id: client

    readonly property string service: "io.github.jmatthiesen81.ClockodoPlasma"
    readonly property string path: "/io/github/jmatthiesen81/ClockodoPlasma"
    readonly property string iface: service

    // Effective language ("de", "en"); the session language until the daemon answers.
    property string language: systemLanguage()

    signal reachableChanged(bool reachable)

    function systemLanguage() {
        const code = Qt.locale().name.split("_")[0];
        return Translations.catalogs[code] ? code : "en";
    }

    function tr(text, arg1, arg2) {
        let args = [];
        if (arg1 !== undefined) {
            args.push(arg1);
        }
        if (arg2 !== undefined) {
            args.push(arg2);
        }
        return Translations.translate(language, text, args);
    }

    function trp(singular, plural, n) {
        return Translations.translatePlural(language, singular, plural, n);
    }

    // Calls a daemon method with string arguments; callbacks get the parsed
    // JSON result (or the raw string) resp. an error message.
    //
    // The Plasma D-Bus module encodes the whole argument list as ONE value of
    // the given signature, so the in-arguments must be wrapped as a struct:
    // "(ss)", not "ss". With "ss" only the first type is used, the list is
    // converted to a single string and the call goes out without arguments
    // ("... with signature "" could not be found").
    function call(member, args, onDone, onError) {
        const stringArgs = (args || []).map(a => new DBus.string(String(a)));
        DBus.SessionBus.asyncCall({
            "service": service,
            "path": path,
            "iface": iface,
            "member": member,
            "arguments": stringArgs,
            "signature": stringArgs.length > 0 ? "(" + "s".repeat(stringArgs.length) + ")" : ""
        }, reply => {
            client.reachableChanged(true);
            if (onDone) {
                let value = reply.value;
                try {
                    value = JSON.parse(value);
                } catch (e) {
                    // plain string result
                }
                onDone(value);
            }
        }, reply => {
            const message = reply && reply.error ? reply.error.message : "D-Bus error";
            console.warn("clockodo-plasma:", member, message);
            if (member === "GetState" || member === "GetSettings") {
                client.reachableChanged(false);
            }
            if (onError) {
                onError(message);
            }
        });
    }
}
