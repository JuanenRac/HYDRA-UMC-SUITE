// =============================================================================
// HYDRA-UMC SUITE - Qt Quick command deck shell
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
//
// Real "redesign from zero" - see qt_suite.py's own module docstring for
// the full account of why (both real ways of embedding QML inside the
// classic QMainWindow+QDockWidget tree failed) and what "not yet
// migrated" placeholders mean here. Same dark navy/cyan "command deck"
// look already established across HYDRA-UMC-OS-REBUILDER/HYDRA-UMC-
// UPDATER/URTC-TESTER/URTC-FLASHER, for ecosystem-wide visual
// consistency - not a new visual language invented for this one app.
// =============================================================================
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.VectorImage

ApplicationWindow {
    id: window
    width: 1920
    height: 1080
    minimumWidth: 1280
    minimumHeight: 800
    visible: true
    title: "HYDRA-UMC SUITE"
    color: "#07111e"

    Component.onCompleted: showMaximized()

    property color panel: "#101d30"
    property color panelAlt: "#14253b"
    property color panelBorder: "#294965"
    property color textPrimary: "#edf7ff"
    property color muted: "#91a8bd"
    property color cyan: "#38d4e6"
    property color amber: "#f7b955"
    property color green: "#43db9b"
    // "root" | "industrial" | "urtc" | "hydraumc" - mirrors
    // NavSidebar's own QStackedWidget page index, named instead of
    // numbered since QML has no equivalent implicit page-order concept
    // worth relying on here.
    property string navPage: "root"

    component Card: Rectangle {
        color: window.panel
        radius: 16
        border.width: 1
        border.color: window.panelBorder
    }

    component SectionLabel: Text {
        color: window.muted
        font.family: "Bahnschrift"
        font.bold: true
        font.pixelSize: 10
        Layout.topMargin: 10
        Layout.leftMargin: 10
    }

    // One real nav leaf (a panel to show) or category (drills into a
    // submenu) - migrated:false shows a small amber dot rather than
    // hiding the item, so every one of the real 26 panels is always
    // reachable and honestly labeled, matching this project's own
    // "never invent/fake completion" convention.
    component NavButton: Rectangle {
        id: navBtn
        property string label: ""
        property bool active: false
        property bool migrated: true
        property bool isCategory: false
        signal activated()
        Layout.fillWidth: true
        Layout.preferredHeight: 32
        radius: 8
        color: navBtn.active ? "#1a4967" : (area.containsMouse ? window.panelAlt : "transparent")
        border.width: navBtn.active ? 1 : 0
        border.color: window.green
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 10
            spacing: 6
            Text {
                text: navBtn.label
                color: navBtn.isCategory ? window.cyan : (navBtn.migrated ? window.textPrimary : window.muted)
                font.family: "Bahnschrift"
                font.bold: navBtn.isCategory
                font.pixelSize: 12
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            Rectangle {
                visible: !navBtn.migrated && !navBtn.isCategory
                width: 6; height: 6; radius: 3
                color: window.amber
            }
            Text {
                visible: navBtn.isCategory
                text: "›"
                color: window.muted
                font.pixelSize: 14
            }
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: navBtn.activated()
        }
    }

    header: ToolBar {
        // Explicit, not left implicit like the sibling apps' own header
        // ToolBars - a real on-screen check here showed those relying on
        // Basic style's own implicit sizing collapsing to 0 height for
        // THIS window (branding/status text all overlapping at the top-
        // left corner instead of laid out in a row). Sized to comfortably
        // fit the 50px icon box plus this Card's own 7px and this
        // RowLayout's own 10px margins top and bottom (50 + 2*7 + 2*10).
        height: 84
        background: Rectangle { color: "#07111e" }
        Card {
            anchors.fill: parent
            anchors.margins: 7
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10
                Rectangle {
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 50
                    radius: 12
                    color: "#0e3045"
                    border.width: 1
                    border.color: "#2d7695"
                    VectorImage { anchors.fill: parent; anchors.margins: 7; source: suiteBackend.iconSource; visible: suiteBackend.iconSource !== "" }
                }
                ColumnLayout {
                    Layout.preferredWidth: 320
                    spacing: 0
                    Text { text: "HYDRA-UMC"; color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 10 }
                    Text { text: "SUITE"; color: window.textPrimary; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 19 }
                    Text { text: suiteBackend.uiText("QT_SUITE_TAGLINE"); color: window.muted; font.family: "Bahnschrift"; font.pixelSize: 8 }
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: suiteBackend.connectionStatus === "connected" ? "● CONNECTED" : (suiteBackend.connectionStatus === "connecting" ? "● CONNECTING" : "● DISCONNECTED")
                    color: suiteBackend.connectionStatus === "connected" ? window.green : (suiteBackend.connectionStatus === "connecting" ? window.amber : window.muted)
                    font.family: "Bahnschrift"
                    font.bold: true
                    font.pixelSize: 11
                }
                Text { text: "v" + suiteBackend.version; color: window.muted; font.family: "Bahnschrift"; font.pixelSize: 10 }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        // -- Nav sidebar - real taxonomy from qt_suite.py's own
        // rootItems/industrialItems/urtcItems/hydraumcItems/
        // hydraumcEcosystemItems, transcribed from nav_sidebar.py's own
        // ROOT_ITEMS/etc. (see that module's own comment). --
        Card {
            Layout.preferredWidth: 260
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 3

                // Root page
                ColumnLayout {
                    visible: window.navPage === "root"
                    Layout.fillWidth: true
                    spacing: 3
                    Repeater {
                        model: suiteBackend.rootItems
                        delegate: NavButton {
                            required property var modelData
                            label: modelData.label
                            migrated: modelData.migrated
                            active: suiteBackend.activePanel === modelData.key
                            onActivated: suiteBackend.navigatePanel(modelData.key)
                        }
                    }
                    SectionLabel { text: suiteBackend.uiText("NAV_SECTION_RESOURCES") }
                    NavButton { label: suiteBackend.uiText("NAV_CATEGORY_INDUSTRIAL"); isCategory: true; onActivated: window.navPage = "industrial" }
                    NavButton { label: suiteBackend.uiText("NAV_CATEGORY_URTC"); isCategory: true; onActivated: window.navPage = "urtc" }
                    NavButton { label: suiteBackend.uiText("NAV_CATEGORY_HYDRA_UMC"); isCategory: true; onActivated: window.navPage = "hydraumc" }
                }

                // Industrial / URTC / HYDRA-UMC submenus - same real
                // back-to-root control nav_sidebar.py's own
                // _build_submenu_page gives each one.
                ColumnLayout {
                    visible: window.navPage !== "root"
                    Layout.fillWidth: true
                    spacing: 3
                    NavButton { label: "‹ " + suiteBackend.uiText("NAV_BACK_TO_ROOT"); onActivated: window.navPage = "root" }
                    SectionLabel {
                        text: window.navPage === "industrial" ? suiteBackend.uiText("NAV_CATEGORY_INDUSTRIAL")
                            : window.navPage === "urtc" ? suiteBackend.uiText("NAV_CATEGORY_URTC")
                            : suiteBackend.uiText("NAV_CATEGORY_HYDRA_UMC")
                    }
                    Repeater {
                        model: window.navPage === "industrial" ? suiteBackend.industrialItems
                            : window.navPage === "urtc" ? suiteBackend.urtcItems
                            : suiteBackend.hydraumcItems
                        delegate: NavButton {
                            required property var modelData
                            label: modelData.label
                            migrated: modelData.migrated
                            active: suiteBackend.activePanel === modelData.key
                            onActivated: suiteBackend.navigatePanel(modelData.key)
                        }
                    }
                    SectionLabel {
                        visible: window.navPage === "hydraumc"
                        text: suiteBackend.uiText("NAV_SECTION_ECOSYSTEM")
                    }
                    Repeater {
                        model: window.navPage === "hydraumc" ? suiteBackend.hydraumcEcosystemItems : []
                        delegate: NavButton {
                            required property var modelData
                            label: modelData.label
                            migrated: modelData.migrated
                            active: suiteBackend.activePanel === modelData.key
                            onActivated: suiteBackend.navigatePanel(modelData.key)
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        // -- Content area - one real panel at a time, matching
        // STUDIO's own nav+single-content-pane shape (see qt_suite.py's
        // own module docstring for why, vs QDockWidget's float/split). --
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Loader {
                id: contentLoader
                anchors.fill: parent
                anchors.margins: 16
                sourceComponent: {
                    if (!suiteBackend.activePanelMigrated) return notMigratedComponent
                    if (suiteBackend.activePanel === "logs") return logsComponent
                    if (suiteBackend.activePanel === "overview") return overviewComponent
                    return notMigratedComponent
                }
            }
        }
    }

    Component {
        id: notMigratedComponent
        ColumnLayout {
            spacing: 12
            Text { text: suiteBackend.uiText("QT_NOT_YET_MIGRATED_TITLE"); color: window.amber; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 18 }
            Text {
                text: suiteBackend.uiText("QT_NOT_YET_MIGRATED_BODY")
                color: window.muted
                font.family: "Bahnschrift"
                wrapMode: Text.WordWrap
                Layout.preferredWidth: 480
            }
        }
    }

    Component {
        id: overviewComponent
        ColumnLayout {
            width: contentLoader.width
            spacing: 14
            Text { text: suiteBackend.uiText("HEADING_OVERVIEW"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            RowLayout {
                Layout.fillWidth: true
                spacing: 14
                Card {
                    Layout.preferredWidth: 320
                    Layout.preferredHeight: 150
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 6
                        Text { text: suiteBackend.uiText("GROUP_ACTIVE_CONTROLLER"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                        GridLayout {
                            columns: 2
                            columnSpacing: 12
                            rowSpacing: 4
                            Text { text: suiteBackend.uiText("LBL_NAME"); color: window.muted; font.pixelSize: 10 }
                            Text { text: suiteBackend.overviewName; color: window.textPrimary; font.pixelSize: 10 }
                            Text { text: suiteBackend.uiText("LBL_IP"); color: window.muted; font.pixelSize: 10 }
                            Text { text: suiteBackend.overviewIp; color: window.textPrimary; font.pixelSize: 10 }
                            Text { text: suiteBackend.uiText("LBL_ROBOTS"); color: window.muted; font.pixelSize: 10 }
                            Text { text: suiteBackend.overviewRobotCount; color: window.textPrimary; font.pixelSize: 10 }
                            Text { text: suiteBackend.uiText("LBL_ONLINE"); color: window.muted; font.pixelSize: 10 }
                            Text { text: suiteBackend.overviewOnlineCount; color: window.textPrimary; font.pixelSize: 10 }
                        }
                    }
                }
                Card {
                    Layout.preferredWidth: 320
                    Layout.preferredHeight: 150
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 6
                        Text { text: suiteBackend.uiText("GROUP_SYSTEM_METRICS"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                        GridLayout {
                            columns: 2
                            columnSpacing: 12
                            rowSpacing: 4
                            Text { text: suiteBackend.uiText("LBL_CPU_LOAD"); color: window.muted; font.pixelSize: 10 }
                            Text { text: suiteBackend.overviewCpu; color: window.textPrimary; font.pixelSize: 10 }
                            Text { text: suiteBackend.uiText("LBL_MEMORY"); color: window.muted; font.pixelSize: 10 }
                            Text { text: suiteBackend.overviewMem; color: window.textPrimary; font.pixelSize: 10 }
                            Text { text: suiteBackend.uiText("LBL_TEMP"); color: window.muted; font.pixelSize: 10 }
                            Text { text: suiteBackend.overviewTemp; color: window.textPrimary; font.pixelSize: 10 }
                            Text { text: suiteBackend.uiText("LBL_UPTIME"); color: window.muted; font.pixelSize: 10 }
                            Text { text: suiteBackend.overviewUptime; color: window.textPrimary; font.pixelSize: 10 }
                        }
                    }
                }
                Item { Layout.fillWidth: true }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.panelBorder }
            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("COL_ROBOT"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 90 }
                Text { text: suiteBackend.uiText("COL_MODEL"); color: window.muted; font.pixelSize: 10; Layout.fillWidth: true }
                Text { text: suiteBackend.uiText("COL_ROLE"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 120 }
                Text { text: suiteBackend.uiText("COL_STATUS"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 90 }
                Text { text: suiteBackend.uiText("COL_SPEED_ACCEL"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 130 }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: suiteBackend.overviewRobots
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width
                    height: 28
                    radius: 6
                    color: index % 2 === 0 ? "transparent" : window.panelAlt
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        Text { text: "#" + modelData.id; color: window.cyan; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 86 }
                        Text { text: modelData.model; color: window.textPrimary; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text { text: modelData.role; color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 120 }
                        Text { text: modelData.status; color: modelData.online ? window.green : window.muted; font.pixelSize: 10; Layout.preferredWidth: 90 }
                        Text { text: modelData.speedAccel; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 130 }
                    }
                }
            }
        }
    }

    Component {
        id: logsComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 10
            Text { text: suiteBackend.uiText("HEADING_LOGS"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { text: suiteBackend.uiText("LBL_LOG_LEVEL"); color: window.muted; font.pixelSize: 10 }
                ComboBox {
                    id: levelCombo
                    model: suiteBackend.logLevels
                    Layout.preferredWidth: 130
                    onActivated: suiteBackend.setLogLevelFilter(currentText)
                }
                TextField {
                    id: searchField
                    placeholderText: suiteBackend.uiText("LOG_SEARCH_PLACEHOLDER")
                    color: window.textPrimary
                    Layout.fillWidth: true
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                    onTextChanged: suiteBackend.setLogSearchFilter(text)
                }
                Button {
                    text: suiteBackend.uiText("BTN_CLEAR_LOGS")
                    onClicked: suiteBackend.clearLogs()
                }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: suiteBackend.logEntries
                onCountChanged: positionViewAtEnd()
                delegate: Text {
                    required property var modelData
                    width: ListView.view.width
                    text: "[" + modelData.level + "] " + modelData.logger + ": " + modelData.message
                    color: modelData.level === "ERROR" || modelData.level === "CRITICAL" ? "#ee6b80"
                        : modelData.level === "WARNING" ? window.amber
                        : modelData.level === "DEBUG" ? "#5f7488" : window.textPrimary
                    font.family: "Cascadia Mono"
                    font.pixelSize: 10
                    wrapMode: Text.WrapAnywhere
                }
            }
        }
    }
}
