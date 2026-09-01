// =============================================================================
// HYDRA-UMC SUITE - Qt Quick command deck
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
// The same QML rendering language used by HYDRA-UMC-UPDATER.  It is a
// presentation and navigation layer over Suite's real Qt dock workspace.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.VectorImage

Rectangle {
    id: deck
    required property var deckBackend
    color: "#07111e"
    implicitHeight: 76
    implicitWidth: 1080

    property color panel: "#101d30"
    property color panelAlt: "#14253b"
    property color border: "#294965"
    property color textPrimary: "#edf7ff"
    property color textMuted: "#91a8bd"
    property color cyan: "#38d4e6"
    property color blue: "#397dff"

    component GameButton: Rectangle {
        id: control
        required property string caption
        required property string route
        color: mouse.pressed ? "#143654" : (mouse.containsMouse ? "#1a4967" : deck.panelAlt)
        radius: 10
        border.width: 1
        border.color: mouse.containsMouse ? deck.cyan : deck.border
        implicitWidth: label.implicitWidth + 28
        implicitHeight: 42
        Behavior on color { ColorAnimation { duration: 130 } }
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 1; color: "#9eeeff"; opacity: mouse.containsMouse ? 0.8 : 0.35 }
        Text {
            id: label; anchors.centerIn: parent; text: control.caption; color: deck.textPrimary
            font.family: "Bahnschrift"; font.pixelSize: 12; font.bold: true
        }
        MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; onClicked: deck.deckBackend.navigate(control.route) }
    }

    component StateChip: Rectangle {
        required property string caption
        required property string value
        required property color valueColor
        color: "#0b1a2a"; radius: 10; border.width: 1; border.color: deck.border
        implicitWidth: 142; implicitHeight: 44
        Column { anchors.centerIn: parent; spacing: 1
            Text { text: parent.caption; color: deck.textMuted; font.family: "Bahnschrift"; font.pixelSize: 9; font.bold: true }
            Text { text: parent.value; color: parent.valueColor; font.family: "Bahnschrift"; font.pixelSize: 10; font.bold: true }
        }
    }

    Rectangle {
        anchors.fill: parent; anchors.margins: 7; radius: 16; color: deck.panel; border.width: 1; border.color: deck.border
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 8
            Rectangle {
                Layout.preferredWidth: 50; Layout.preferredHeight: 50; radius: 12; color: "#0e3045"; border.width: 1; border.color: "#2d7695"
                VectorImage { anchors.fill: parent; anchors.margins: 7; source: deck.deckBackend.logoSource }
            }
            ColumnLayout { Layout.preferredWidth: 176; spacing: 0
                Text { text: "HYDRA-UMC"; color: deck.cyan; font.family: "Bahnschrift"; font.pixelSize: 10; font.bold: true }
                Text { text: deck.deckBackend.title; color: deck.textPrimary; font.family: "Bahnschrift"; font.pixelSize: 17; font.bold: true }
                Text { text: "MISSION CONTROL  •  LIVE WORKSPACE"; color: deck.textMuted; font.family: "Bahnschrift"; font.pixelSize: 8; font.bold: true }
            }
            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; Layout.topMargin: 10; Layout.bottomMargin: 10; color: deck.border }
            GameButton { caption: "OVERVIEW"; route: "overview" }
            GameButton { caption: "ROBOT"; route: "robot" }
            GameButton { caption: "CAMERAS"; route: "cameras" }
            GameButton { caption: "TRAJECTORY"; route: "trajectory" }
            GameButton { caption: "LOGS"; route: "logs" }
            Item { Layout.fillWidth: true }
            StateChip { caption: "SYSTEM STATE"; value: "● " + deck.deckBackend.status; valueColor: deck.deckBackend.statusColor }
            StateChip { caption: "ACTIVE TARGET"; value: deck.deckBackend.target; valueColor: deck.textPrimary }
            StateChip { caption: "UTC"; value: deck.deckBackend.clock; valueColor: deck.textMuted }
            GameButton { caption: "ABOUT"; route: "about" }
        }
    }
}
