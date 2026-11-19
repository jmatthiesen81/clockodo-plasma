// SPDX-License-Identifier: MPL-2.0
import QtQuick
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami

// Small upper-case heading above a group in the popup.
PlasmaComponents3.Label {
    font.bold: true
    font.capitalization: Font.AllUppercase
    font.pointSize: Kirigami.Theme.smallFont.pointSize
    opacity: 0.7
}
