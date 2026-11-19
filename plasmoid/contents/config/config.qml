// SPDX-License-Identifier: MPL-2.0
import QtQuick
import org.kde.plasma.configuration
import "../ui/translations.js" as Translations

// Pages of the widget's configuration dialog. Category names follow the
// session language; the pages themselves use the language chosen in the
// settings (they ask the daemon).
ConfigModel {
    id: model

    readonly property string language: {
        const code = Qt.locale().name.split("_")[0];
        return Translations.catalogs[code] ? code : "en";
    }

    function tr(text) {
        return Translations.translate(language, text, []);
    }

    ConfigCategory {
        name: model.tr("Default booking")
        icon: "media-playback-start"
        source: "ConfigBooking.qml"
    }
    ConfigCategory {
        name: model.tr("Controls")
        icon: "input-mouse"
        source: "ConfigControls.qml"
    }
    ConfigCategory {
        name: model.tr("Reminders")
        icon: "notifications"
        source: "ConfigReminders.qml"
    }
    ConfigCategory {
        name: model.tr("General")
        icon: "preferences-system"
        source: "ConfigGeneral.qml"
    }
    ConfigCategory {
        name: model.tr("Account")
        icon: "im-user"
        source: "ConfigAccount.qml"
    }
}
