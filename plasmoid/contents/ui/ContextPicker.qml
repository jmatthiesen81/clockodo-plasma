// SPDX-License-Identifier: MPL-2.0
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami

// Explicit choice of customer › project › service, with the recently used
// contexts as shortcuts. Emits picked(ctx); never starts anything itself.
ColumnLayout {
    id: picker

    property var contexts: null
    property var selected: null
    signal picked(var ctx)

    spacing: Kirigami.Units.smallSpacing

    readonly property var customers: contexts ? contexts.customers : []
    readonly property var services: contexts ? contexts.services : []
    readonly property var projects: {
        if (!contexts || !selected || !selected.customers_id) {
            return [];
        }
        return contexts.projects.filter(p => p.customers_id === selected.customers_id);
    }
    readonly property var projectChoices: [{ "id": 0, "name": root.tr("– no project –") }].concat(projects)
    readonly property var recentChoices: contexts ? contexts.recent : []

    function indexOfId(list, id) {
        for (let i = 0; i < list.length; ++i) {
            if (list[i].id === id) {
                return i;
            }
        }
        return -1;
    }

    function update(changes) {
        let ctx = Object.assign({ "customers_id": 0, "projects_id": 0, "services_id": 0 }, selected || {});
        Object.assign(ctx, changes);
        picked(ctx);
    }

    PlasmaComponents3.Label {
        visible: picker.recentChoices.length > 0
        text: root.tr("Recently used")
        opacity: 0.8
    }

    PlasmaComponents3.ComboBox {
        Layout.fillWidth: true
        visible: picker.recentChoices.length > 0
        model: picker.recentChoices
        textRole: "label"
        currentIndex: -1
        displayText: currentIndex < 0 ? root.tr("Choose a recent context…") : currentText
        onActivated: index => picker.picked(picker.recentChoices[index])
        Accessible.name: root.tr("Recently used")
    }

    Kirigami.FormLayout {
        Layout.fillWidth: true

        PlasmaComponents3.ComboBox {
            Kirigami.FormData.label: root.tr("Customer:")
            Layout.fillWidth: true
            model: picker.customers
            textRole: "name"
            currentIndex: picker.selected ? picker.indexOfId(picker.customers, picker.selected.customers_id) : -1
            displayText: currentIndex < 0 ? root.tr("Choose…") : currentText
            onActivated: index => picker.update({
                "customers_id": picker.customers[index].id,
                "projects_id": 0
            })
            Accessible.name: root.tr("Customer")
        }

        PlasmaComponents3.ComboBox {
            Kirigami.FormData.label: root.tr("Project:")
            Layout.fillWidth: true
            enabled: !!picker.selected && !!picker.selected.customers_id
            model: picker.projectChoices
            textRole: "name"
            currentIndex: picker.selected
                ? Math.max(0, picker.indexOfId(picker.projectChoices, picker.selected.projects_id || 0))
                : 0
            onActivated: index => picker.update({ "projects_id": picker.projectChoices[index].id })
            Accessible.name: root.tr("Project")
        }

        PlasmaComponents3.ComboBox {
            Kirigami.FormData.label: root.tr("Service:")
            Layout.fillWidth: true
            model: picker.services
            textRole: "name"
            currentIndex: picker.selected ? picker.indexOfId(picker.services, picker.selected.services_id) : -1
            displayText: currentIndex < 0 ? root.tr("Choose…") : currentText
            onActivated: index => picker.update({ "services_id": picker.services[index].id })
            Accessible.name: root.tr("Service")
        }
    }
}
