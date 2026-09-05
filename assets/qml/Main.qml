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
import QtQuick.Dialogs
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
    // Which server row's credentials the shared dialog below is
    // currently editing - "" when none.
    property string credentialsConnId: ""

    // Generic destructive-action confirm, shared by any panel that
    // needs one (Admin Server's own restart today) - same real shape
    // as URTC-FLASHER's own requestConfigWrite/configConfirm.
    property string pendingConfirmTitle: ""
    property string pendingConfirmBody: ""
    property var pendingConfirmAction: null

    function requestConfirm(title, body, action) {
        pendingConfirmTitle = title
        pendingConfirmBody = body
        pendingConfirmAction = action
        confirmDialog.open()
    }

    function openCredentials(connId) {
        var creds = suiteBackend.serverCredentials(connId)
        window.credentialsConnId = connId
        credentialsUsernameField.text = creds.username
        credentialsPasswordField.text = creds.password
        credentialsDialog.open()
    }

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

    // Real, shared credentials editor - ported from server_browser.py's
    // own CredentialsDialog (a small modal QDialog there). Opened via
    // window.openCredentials(connId), which pre-fills both fields from
    // the real, currently-stored values.
    Dialog {
        id: credentialsDialog
        anchors.centerIn: parent
        modal: true
        width: 360
        title: suiteBackend.uiText("TITLE_EDIT_CREDENTIALS")
        standardButtons: Dialog.Ok | Dialog.Cancel
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        contentItem: ColumnLayout {
            spacing: 10
            RowLayout {
                Text { text: suiteBackend.uiText("LBL_USERNAME"); color: window.muted; Layout.preferredWidth: 90 }
                TextField {
                    id: credentialsUsernameField
                    Layout.fillWidth: true
                    color: window.textPrimary
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                }
            }
            RowLayout {
                Text { text: suiteBackend.uiText("LBL_PASSWORD"); color: window.muted; Layout.preferredWidth: 90 }
                TextField {
                    id: credentialsPasswordField
                    Layout.fillWidth: true
                    echoMode: TextInput.Password
                    color: window.textPrimary
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                }
            }
        }
        onAccepted: suiteBackend.saveServerCredentials(window.credentialsConnId, credentialsUsernameField.text, credentialsPasswordField.text)
    }

    FileDialog {
        id: xyTableSaveDialog
        title: suiteBackend.uiText("BTN_SAVE_CONFIG")
        fileMode: FileDialog.SaveFile
        nameFilters: ["JSON (*.json)"]
        onAccepted: suiteBackend.saveXyTableConfig(selectedFile.toString())
    }

    Dialog {
        id: confirmDialog
        anchors.centerIn: parent
        modal: true
        width: 420
        title: window.pendingConfirmTitle
        standardButtons: Dialog.Cancel
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: window.pendingConfirmBody; color: window.textPrimary; wrapMode: Text.WordWrap; Layout.preferredWidth: 380 }
            Button {
                text: suiteBackend.uiText("BTN_SAVE")
                Layout.fillWidth: true
                onClicked: { confirmDialog.close(); if (window.pendingConfirmAction) window.pendingConfirmAction() }
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
                    if (suiteBackend.activePanel === "servers") return serversComponent
                    if (suiteBackend.activePanel === "robot") return robotComponent
                    if (suiteBackend.activePanel === "trajectory") return trajectoryComponent
                    if (suiteBackend.activePanel === "ai_family") return aiFamilyComponent
                    if (suiteBackend.activePanel === "admin_clients") return adminClientsComponent
                    if (suiteBackend.activePanel === "admin_logs") return adminLogsComponent
                    if (suiteBackend.activePanel === "admin_server") return adminServerComponent
                    if (suiteBackend.activePanel === "ecosystem_services") return ecosystemServicesComponent
                    if (suiteBackend.activePanel === "ecosystem_telemetry") return ecosystemTelemetryComponent
                    if (suiteBackend.activePanel === "xy_table") return xyTableComponent
                    if (suiteBackend.activePanel === "rack") return rackComponent
                    if (suiteBackend.activePanel === "pick_and_place") return pickAndPlaceComponent
                    if (suiteBackend.activePanel === "kinematic_brain_stage") return kinematicBrainStageComponent
                    if (suiteBackend.activePanel === "cnc") return moduleConfigComponent
                    if (suiteBackend.activePanel === "laser") return moduleConfigComponent
                    if (suiteBackend.activePanel === "heated_bed") return moduleConfigComponent
                    if (suiteBackend.activePanel === "vacuum_table") return moduleConfigComponent
                    if (suiteBackend.activePanel === "atc") return atcComponent
                    if (suiteBackend.activePanel === "cameras") return camerasComponent
                    if (suiteBackend.activePanel === "urtc_flasher") return flasherComponent
                    if (suiteBackend.activePanel === "hydra_flasher") return flasherComponent
                    if (suiteBackend.activePanel === "urtc_tester") return testerComponent
                    if (suiteBackend.activePanel === "hydra_tester") return testerComponent
                    if (suiteBackend.activePanel === "viewport") return viewportComponent
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
        id: serversComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 10
            Text { text: suiteBackend.uiText("HEADING_SERVERS"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Button {
                    text: suiteBackend.serverScanning ? "..." : suiteBackend.uiText("BTN_SCAN_NETWORK")
                    enabled: !suiteBackend.serverScanning
                    onClicked: suiteBackend.scanServers()
                }
                Text { text: suiteBackend.serverScanStatus; color: window.muted; font.pixelSize: 10 }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.panelBorder }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                TextField {
                    id: hostField
                    placeholderText: suiteBackend.uiText("PLACEHOLDER_HOST")
                    color: window.textPrimary
                    Layout.fillWidth: true
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                }
                SpinBox {
                    id: portSpin
                    from: 1; to: 65535
                    value: suiteBackend.defaultServerPort
                    editable: true
                    Layout.preferredWidth: 140
                }
                TextField {
                    id: userField
                    placeholderText: suiteBackend.uiText("LBL_USERNAME")
                    color: window.textPrimary
                    Layout.preferredWidth: 110
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                }
                TextField {
                    id: passField
                    placeholderText: suiteBackend.uiText("LBL_PASSWORD")
                    echoMode: TextInput.Password
                    color: window.textPrimary
                    Layout.preferredWidth: 110
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                }
                Button {
                    text: suiteBackend.uiText("BTN_ADD")
                    onClicked: {
                        suiteBackend.addManualServer(hostField.text, portSpin.value, userField.text, passField.text)
                        hostField.text = ""
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.panelBorder }
            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("COL_SERVER"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 200 }
                Text { text: suiteBackend.uiText("COL_HOST"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 180 }
                Text { text: suiteBackend.uiText("COL_ROBOTS"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 80 }
                Text { text: suiteBackend.uiText("COL_STATUS"); color: window.muted; font.pixelSize: 10; Layout.fillWidth: true }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: suiteBackend.serverRows
                spacing: 4
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width
                    height: 34
                    radius: 8
                    color: modelData.active ? "#1a4967" : window.panelAlt
                    border.width: modelData.active ? 1 : 0
                    border.color: window.green
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        Text { text: modelData.name; color: window.textPrimary; font.bold: modelData.active; font.pixelSize: 11; Layout.preferredWidth: 192; elide: Text.ElideRight }
                        Text { text: modelData.hostPort; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 172 }
                        Text { text: modelData.robotCount; color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 72 }
                        Text {
                            text: modelData.statusText
                            color: modelData.statusText === suiteBackend.uiText("STATUS_CONNECTED") ? window.green
                                : (modelData.loginDetail !== "" ? "#ee6b80" : window.amber)
                            font.pixelSize: 10
                            Layout.fillWidth: true
                            ToolTip.visible: modelData.loginDetail !== "" && statusHover.hovered
                            ToolTip.text: modelData.loginDetail
                            HoverHandler { id: statusHover }
                        }
                        Button { text: suiteBackend.uiText("BTN_SET_ACTIVE"); implicitHeight: 26; onClicked: suiteBackend.setActiveServer(modelData.connId) }
                        Button { text: suiteBackend.uiText("BTN_EDIT_CREDENTIALS"); implicitHeight: 26; onClicked: window.openCredentials(modelData.connId) }
                        Button { text: suiteBackend.uiText("BTN_REMOVE_SELECTED"); implicitHeight: 26; onClicked: suiteBackend.removeServer(modelData.connId) }
                    }
                }
            }
        }
    }

    Component {
        id: robotComponent
        ColumnLayout {
            width: contentLoader.width
            spacing: 14
            Text { text: suiteBackend.uiText("HEADING_ROBOT_CONTROL"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            ComboBox {
                id: robotCombo
                Layout.preferredWidth: 260
                model: suiteBackend.robotOptions
                textRole: "label"
                valueRole: "id"
                Component.onCompleted: currentIndex = indexOfValue(suiteBackend.selectedRobotId)
                Connections {
                    target: suiteBackend
                    function onChanged() {
                        var idx = robotCombo.indexOfValue(suiteBackend.selectedRobotId)
                        if (idx !== robotCombo.currentIndex) robotCombo.currentIndex = idx
                    }
                }
                onActivated: suiteBackend.selectRobot(currentValue)
            }
            Card {
                Layout.fillWidth: true
                Layout.preferredHeight: jointsColumn.implicitHeight + 28
                ColumnLayout {
                    id: jointsColumn
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Text { text: suiteBackend.uiText("GROUP_JOINTS"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                    Repeater {
                        model: suiteBackend.selectedRobotJoints
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 8
                            Text { text: modelData.name.toUpperCase(); color: window.muted; font.bold: true; Layout.preferredWidth: 30 }
                            Slider {
                                Layout.fillWidth: true
                                from: -180; to: 180
                                value: modelData.value
                                enabled: suiteBackend.canControlRobot
                                onMoved: suiteBackend.setJoint(modelData.name, value)
                            }
                            Text { text: modelData.value.toFixed(1) + "°"; color: window.textPrimary; font.family: "Cascadia Mono"; Layout.preferredWidth: 55 }
                        }
                    }
                }
            }
            Card {
                Layout.fillWidth: true
                Layout.preferredHeight: 100
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Text { text: suiteBackend.uiText("GROUP_PLAYBACK"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: suiteBackend.uiText("LBL_SPEED"); color: window.muted; Layout.preferredWidth: 90 }
                        Slider { Layout.fillWidth: true; from: 1; to: 200; value: suiteBackend.selectedRobotSpeed; enabled: suiteBackend.canControlRobot; onMoved: suiteBackend.setRobotSpeed(Math.round(value)) }
                        Text { text: suiteBackend.selectedRobotSpeed + "%"; color: window.textPrimary; Layout.preferredWidth: 45 }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: suiteBackend.uiText("LBL_ACCELERATION"); color: window.muted; Layout.preferredWidth: 90 }
                        Slider { Layout.fillWidth: true; from: 1; to: 200; value: suiteBackend.selectedRobotAcceleration; enabled: suiteBackend.canControlRobot; onMoved: suiteBackend.setRobotAcceleration(Math.round(value)) }
                        Text { text: suiteBackend.selectedRobotAcceleration + "%"; color: window.textPrimary; Layout.preferredWidth: 45 }
                    }
                }
            }
            Item { Layout.fillHeight: true }
        }
    }

    Component {
        id: trajectoryComponent
        ColumnLayout {
            id: trajectoryRoot
            width: contentLoader.width
            height: contentLoader.height
            spacing: 10
            property int selectedRow: -1
            Text { text: suiteBackend.uiText("HEADING_TRAJECTORY"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            Text { text: suiteBackend.selectedRobotLabel; color: window.muted; font.pixelSize: 11 }
            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("COL_TIME"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 100 }
                Text { text: suiteBackend.uiText("HEADING_ROBOT_CONTROL") + " (J1…J6)"; color: window.muted; font.pixelSize: 10; Layout.fillWidth: true }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: suiteBackend.trajectoryPoints
                spacing: 3
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: ListView.view.width
                    height: 28
                    radius: 6
                    color: trajectoryRoot.selectedRow === index ? "#1a4967" : (index % 2 === 0 ? "transparent" : window.panelAlt)
                    border.width: trajectoryRoot.selectedRow === index ? 1 : 0
                    border.color: window.green
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        Text { text: modelData.time; color: window.textPrimary; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 94 }
                        Text { text: modelData.joints; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.fillWidth: true }
                    }
                    MouseArea { anchors.fill: parent; onClicked: trajectoryRoot.selectedRow = index }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Button {
                    text: suiteBackend.uiText("BTN_RECORD_POSE")
                    enabled: suiteBackend.canControlRobot
                    onClicked: {
                        suiteBackend.recordTrajectoryPoint()
                        trajectoryRoot.selectedRow = suiteBackend.trajectoryPoints.length - 1
                    }
                }
                Button {
                    text: suiteBackend.uiText("BTN_JOG_TO_POINT")
                    enabled: suiteBackend.canControlRobot && trajectoryRoot.selectedRow >= 0
                    onClicked: suiteBackend.applyTrajectoryPoint(trajectoryRoot.selectedRow)
                }
                Button {
                    text: suiteBackend.uiText("BTN_DELETE_POINT")
                    enabled: trajectoryRoot.selectedRow >= 0
                    onClicked: {
                        suiteBackend.deleteTrajectoryPoint(trajectoryRoot.selectedRow)
                        trajectoryRoot.selectedRow = -1
                    }
                }
            }
        }
    }

    Component {
        id: aiFamilyComponent
        ColumnLayout {
            width: contentLoader.width
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("HEADING_AI_FAMILY"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                Button {
                    text: suiteBackend.aiFamilyRefreshing ? "..." : suiteBackend.uiText("BTN_REFRESH")
                    enabled: !suiteBackend.aiFamilyRefreshing
                    onClicked: suiteBackend.refreshAiFamily()
                }
            }
            Text {
                visible: suiteBackend.aiFamilyStatusText !== ""
                text: suiteBackend.aiFamilyStatusText
                color: window.muted
                font.pixelSize: 11
            }
            Repeater {
                model: suiteBackend.aiFamilyGroups
                delegate: ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: modelData.title; color: window.muted; font.bold: true; font.pixelSize: 10 }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            radius: 9
                            implicitHeight: 20
                            implicitWidth: pillText.implicitWidth + 18
                            color: modelData.deviceConfigured ? "#123a4a" : window.panelAlt
                            Text { id: pillText; anchors.centerIn: parent; text: modelData.devicePill; color: modelData.deviceConfigured ? "#4fc3f7" : window.muted; font.bold: true; font.pixelSize: 9 }
                        }
                    }
                    Text {
                        visible: modelData.mismatchWarning !== ""
                        text: modelData.mismatchWarning
                        color: window.amber
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.pixelSize: 10
                    }
                    GridLayout {
                        columns: 2
                        columnSpacing: 8
                        rowSpacing: 8
                        Layout.fillWidth: true
                        Repeater {
                            model: modelData.projects
                            delegate: Card {
                                required property var modelData
                                Layout.preferredWidth: 360
                                Layout.preferredHeight: 46
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    ColumnLayout {
                                        spacing: 2
                                        Layout.fillWidth: true
                                        Text { text: modelData.name; color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                                        Text { text: modelData.meta; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 9 }
                                    }
                                    Text {
                                        text: modelData.statusText
                                        color: modelData.live === true ? window.green : (modelData.live === false ? "#ee6b80" : window.muted)
                                        font.bold: true
                                        font.pixelSize: 9
                                    }
                                }
                            }
                        }
                    }
                    Text {
                        visible: modelData.projects.length === 0
                        text: suiteBackend.uiText("MSG_ES_NONE")
                        color: "#556070"
                        font.pixelSize: 10
                    }
                    Text { text: modelData.countText; color: "#556070"; font.pixelSize: 9 }
                }
            }
            Item { Layout.fillHeight: true }
        }
    }

    Component {
        id: adminClientsComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 10
            Text { text: suiteBackend.uiText("HEADING_ADMIN_CLIENTS"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            Text { text: suiteBackend.adminClientsStatusText; color: window.muted; font.pixelSize: 11 }
            RowLayout {
                visible: suiteBackend.adminClientsShowStats
                spacing: 10
                Card {
                    Layout.preferredWidth: 140
                    Layout.preferredHeight: 60
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2
                        Text { text: suiteBackend.uiText("LBL_CLIENTS_STAT_CONNECTED"); color: window.muted; font.pixelSize: 9; font.bold: true }
                        Text { text: suiteBackend.adminClientsConnectedCount; color: window.textPrimary; font.pixelSize: 20; font.bold: true }
                    }
                }
                Card {
                    Layout.preferredWidth: 140
                    Layout.preferredHeight: 60
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2
                        Text { text: suiteBackend.uiText("LBL_CLIENTS_STAT_ADMINS"); color: window.muted; font.pixelSize: 9; font.bold: true }
                        Text { text: suiteBackend.adminClientsAdminCount; color: window.textPrimary; font.pixelSize: 20; font.bold: true }
                    }
                }
            }
            Text {
                // Same real unconditional behavior as
                // admin_clients_panel.py's own _rebuild(): shown
                // whenever the list is empty, whatever the reason
                // (no active server / not admin / genuinely zero
                // clients) - the status text above already explains why.
                visible: suiteBackend.adminClientsRows.length === 0
                text: suiteBackend.uiText("MSG_CLIENTS_NONE")
                color: "#556070"
                font.pixelSize: 11
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: suiteBackend.adminClientsRows
                spacing: 4
                delegate: Card {
                    required property var modelData
                    width: ListView.view.width
                    height: 42
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10
                        Rectangle {
                            width: 24; height: 24; radius: 12
                            color: modelData.isAdmin ? "#123a1c" : "#0e2a3a"
                            Text { anchors.centerIn: parent; text: modelData.isAdmin ? "A" : "U"; color: modelData.isAdmin ? window.green : "#38bdf8"; font.bold: true; font.pixelSize: 10 }
                        }
                        ColumnLayout {
                            spacing: 2
                            Layout.fillWidth: true
                            Text { text: modelData.username; color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                            Text { text: modelData.address; color: "#556070"; font.family: "Cascadia Mono"; font.pixelSize: 9 }
                        }
                        Text { text: modelData.roleLabel; color: modelData.isAdmin ? window.green : "#38bdf8"; font.bold: true; font.pixelSize: 9 }
                        Text { text: modelData.duration; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 9 }
                        Text { text: "●"; color: modelData.connected ? window.green : "#ee6b80"; font.pixelSize: 10 }
                    }
                }
            }
        }
    }

    Component {
        id: adminLogsComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("HEADING_ADMIN_LOGS"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                Button { text: suiteBackend.uiText("BTN_CLEAR"); onClicked: suiteBackend.clearAdminLogs() }
                Button { text: suiteBackend.adminLogsLive ? suiteBackend.uiText("BTN_PAUSE") : suiteBackend.uiText("BTN_RESUME"); onClicked: suiteBackend.toggleAdminLogsLive() }
            }
            Text { text: suiteBackend.adminLogsStatusText; color: window.muted; font.pixelSize: 11 }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                TextField {
                    placeholderText: suiteBackend.uiText("LOGS_SEARCH_PLACEHOLDER")
                    color: window.textPrimary
                    Layout.preferredWidth: 260
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                    onTextChanged: suiteBackend.setAdminLogsSearch(text)
                }
                Button {
                    text: suiteBackend.uiText("LOGS_ALL_TAGS")
                    checkable: true
                    checked: suiteBackend.adminLogsTagFilter === ""
                    onClicked: suiteBackend.setAdminLogsTagFilter("")
                }
                Repeater {
                    model: suiteBackend.adminLogsTags
                    delegate: Button {
                        required property string modelData
                        text: modelData
                        checkable: true
                        checked: suiteBackend.adminLogsTagFilter === modelData
                        onClicked: suiteBackend.setAdminLogsTagFilter(modelData)
                    }
                }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: suiteBackend.adminLogsLines
                delegate: Text {
                    required property string modelData
                    width: ListView.view.width
                    text: modelData
                    color: window.muted
                    font.family: "Cascadia Mono"
                    font.pixelSize: 10
                    wrapMode: Text.WrapAnywhere
                }
            }
        }
    }

    Component {
        id: adminServerComponent
        ColumnLayout {
            width: contentLoader.width
            spacing: 12
            Text { text: suiteBackend.uiText("HEADING_ADMIN_SERVER"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            Text { text: suiteBackend.adminServerStatusText; color: window.muted; font.pixelSize: 11 }
            Card {
                visible: suiteBackend.adminServerInfoVisible
                Layout.fillWidth: true
                Layout.preferredHeight: 80
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 6
                    RowLayout {
                        Text { text: suiteBackend.adminServerProduct; color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        Item { Layout.fillWidth: true }
                        Text { text: suiteBackend.adminServerVersion; color: "#556070"; font.family: "Cascadia Mono"; font.pixelSize: 9 }
                    }
                    RowLayout {
                        spacing: 24
                        ColumnLayout {
                            spacing: 1
                            Text { text: suiteBackend.uiText("LBL_ADMIN_SERVER_STAT_UPTIME"); color: window.muted; font.pixelSize: 8 }
                            Text { text: suiteBackend.adminServerUptime; color: window.textPrimary; font.family: "Cascadia Mono"; font.bold: true; font.pixelSize: 11 }
                        }
                        ColumnLayout {
                            spacing: 1
                            Text { text: suiteBackend.uiText("LBL_ADMIN_SERVER_STAT_CONTROLLERS"); color: window.muted; font.pixelSize: 8 }
                            Text { text: suiteBackend.adminServerControllerCount; color: window.textPrimary; font.family: "Cascadia Mono"; font.bold: true; font.pixelSize: 11 }
                        }
                        ColumnLayout {
                            spacing: 1
                            Text { text: suiteBackend.uiText("LBL_ADMIN_SERVER_STAT_ROBOTS"); color: window.muted; font.pixelSize: 8 }
                            Text { text: suiteBackend.adminServerRobotCount; color: window.textPrimary; font.family: "Cascadia Mono"; font.bold: true; font.pixelSize: 11 }
                        }
                        ColumnLayout {
                            spacing: 1
                            Text { text: suiteBackend.uiText("LBL_ADMIN_SERVER_STAT_HOST"); color: window.muted; font.pixelSize: 8 }
                            Text { text: suiteBackend.adminServerHost; color: window.textPrimary; font.family: "Cascadia Mono"; font.bold: true; font.pixelSize: 11 }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text { text: suiteBackend.adminServerPortLabel; color: window.muted; font.pixelSize: 11 }
                TextField {
                    id: portField
                    text: suiteBackend.adminServerPendingPortText
                    color: window.textPrimary
                    Layout.preferredWidth: 100
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                }
                Button { text: suiteBackend.uiText("BTN_SAVE"); onClicked: suiteBackend.saveAdminServerPort(portField.text) }
            }
            Text {
                text: suiteBackend.uiText("MSG_ADMIN_SERVER_PORT_NOTE")
                color: window.amber
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                font.pixelSize: 10
            }
            Button {
                id: restartButton
                text: suiteBackend.uiText("BTN_RESTART_SERVER")
                onClicked: window.requestConfirm(
                    suiteBackend.uiText("TITLE_RESTART_SERVER"),
                    suiteBackend.uiText("MSG_ADMIN_SERVER_RESTART_CONFIRM"),
                    function() { suiteBackend.restartAdminServer() })
                contentItem: Text { text: restartButton.text; color: "#ee6b80"; horizontalAlignment: Text.AlignHCenter }
            }
            Item { Layout.fillHeight: true }
        }
    }

    component EsStatBox: Card {
        id: esStatBoxRoot
        property string caption: ""
        property string value: ""
        Layout.preferredWidth: 90
        Layout.preferredHeight: 50
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 2
            Text { text: esStatBoxRoot.caption; color: window.muted; font.pixelSize: 8; font.bold: true }
            Text { text: esStatBoxRoot.value; color: window.textPrimary; font.pixelSize: 16; font.bold: true }
        }
    }

    Component {
        id: ecosystemServicesComponent
        ColumnLayout {
            width: contentLoader.width
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("HEADING_ECOSYSTEM_SERVICES"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                Button {
                    text: suiteBackend.esRefreshing ? "..." : suiteBackend.uiText("BTN_REFRESH")
                    enabled: !suiteBackend.esRefreshing
                    onClicked: suiteBackend.refreshEcosystemServices()
                }
            }
            Text { text: suiteBackend.esStatusText; color: window.muted; font.pixelSize: 11 }
            RowLayout {
                visible: suiteBackend.esShowStats
                spacing: 8
                EsStatBox { caption: suiteBackend.uiText("LBL_SERVICES_STAT_TOTAL"); value: suiteBackend.esStats.total }
                EsStatBox { caption: suiteBackend.uiText("LBL_SERVICES_STAT_LIVE"); value: suiteBackend.esStats.live }
                EsStatBox { caption: suiteBackend.uiText("LBL_SERVICES_STAT_FAMILIES"); value: suiteBackend.esStats.families }
                EsStatBox { caption: suiteBackend.uiText("LBL_SERVICES_STAT_RUNNING"); value: suiteBackend.esStats.running }
                EsStatBox { caption: suiteBackend.uiText("LBL_SERVICES_STAT_STOPPED"); value: suiteBackend.esStats.stopped }
                EsStatBox { caption: suiteBackend.uiText("LBL_SERVICES_STAT_ERROR"); value: suiteBackend.esStats.error }
                EsStatBox { caption: suiteBackend.uiText("LBL_SERVICES_STAT_NA"); value: suiteBackend.esStats.na }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                TextField {
                    placeholderText: suiteBackend.uiText("SERVICES_SEARCH_PLACEHOLDER")
                    color: window.textPrimary
                    Layout.preferredWidth: 220
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                    onTextChanged: suiteBackend.setEsSearch(text)
                }
                Button {
                    text: suiteBackend.uiText("SERVICES_ALL_FAMILIES")
                    checkable: true
                    checked: suiteBackend.esFamilyFilter === ""
                    onClicked: suiteBackend.setEsFamilyFilter("")
                }
                Repeater {
                    model: suiteBackend.esFamilies
                    delegate: Button {
                        required property string modelData
                        text: modelData
                        checkable: true
                        checked: suiteBackend.esFamilyFilter === modelData
                        onClicked: suiteBackend.setEsFamilyFilter(modelData)
                    }
                }
            }
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: esColumn.implicitHeight
                clip: true
                ColumnLayout {
                    id: esColumn
                    width: parent.width
                    spacing: 10
                    Repeater {
                        model: suiteBackend.esGroups
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 6
                            Text { text: modelData.family + "  (" + modelData.count + ")"; color: window.muted; font.bold: true; font.pixelSize: 10 }
                            GridLayout {
                                columns: 3
                                columnSpacing: 8
                                rowSpacing: 8
                                Layout.fillWidth: true
                                Repeater {
                                    model: modelData.cards
                                    delegate: Card {
                                        id: serviceCard
                                        required property var modelData
                                        Layout.preferredWidth: 260
                                        Layout.preferredHeight: 110
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 4
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Text { text: serviceCard.modelData.name; color: window.textPrimary; font.bold: true; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                                Rectangle {
                                                    radius: 6
                                                    implicitWidth: badgeCol.implicitWidth + 12
                                                    implicitHeight: badgeCol.implicitHeight + 6
                                                    color: serviceCard.modelData.healthColorBg
                                                    border.width: 1
                                                    border.color: serviceCard.modelData.healthColorBorder
                                                    ColumnLayout {
                                                        id: badgeCol
                                                        anchors.centerIn: parent
                                                        spacing: 0
                                                        Text { text: "● " + serviceCard.modelData.badgeText; color: serviceCard.modelData.healthColor; font.bold: true; font.pixelSize: 8 }
                                                        Text { visible: serviceCard.modelData.version !== ""; text: serviceCard.modelData.version; color: serviceCard.modelData.healthColor; font.bold: true; font.pixelSize: 12; font.family: "Cascadia Mono" }
                                                    }
                                                }
                                            }
                                            RowLayout {
                                                spacing: 8
                                                Text { visible: serviceCard.modelData.stack !== ""; text: serviceCard.modelData.stack; color: serviceCard.modelData.stackColor; font.bold: true; font.pixelSize: 8 }
                                                Text { visible: serviceCard.modelData.maturity !== ""; text: serviceCard.modelData.maturity; color: "#556070"; font.bold: true; font.pixelSize: 8 }
                                                Item { Layout.fillWidth: true }
                                            }
                                            Text {
                                                visible: serviceCard.modelData.hostPort !== "" || serviceCard.modelData.pidText !== ""
                                                text: [serviceCard.modelData.hostPort, serviceCard.modelData.pidText].filter(function(s) { return s !== "" }).join("  ")
                                                color: "#556070"
                                                font.family: "Cascadia Mono"
                                                font.pixelSize: 9
                                            }
                                            RowLayout {
                                                visible: serviceCard.modelData.canControl
                                                spacing: 6
                                                Text {
                                                    visible: serviceCard.modelData.actioning
                                                    text: suiteBackend.uiText("LBL_SERVICES_ACTION_PENDING")
                                                    color: window.muted
                                                    font.pixelSize: 8
                                                    font.bold: true
                                                }
                                                Button {
                                                    visible: !serviceCard.modelData.actioning
                                                    text: suiteBackend.uiText("BTN_SERVICES_START")
                                                    implicitHeight: 22
                                                    contentItem: Text { text: suiteBackend.uiText("BTN_SERVICES_START"); color: "#4caf50"; font.pixelSize: 9 }
                                                    onClicked: suiteBackend.runEsServiceAction(serviceCard.modelData.unit, "start")
                                                }
                                                Button {
                                                    visible: !serviceCard.modelData.actioning
                                                    implicitHeight: 22
                                                    contentItem: Text { text: suiteBackend.uiText("BTN_SERVICES_STOP"); color: "#e05050"; font.pixelSize: 9 }
                                                    onClicked: window.requestConfirm(
                                                        suiteBackend.uiText("TITLE_SERVICES_CONFIRM_STOP"),
                                                        suiteBackend.uiText("MSG_SERVICES_CONFIRM_STOP").replace("{name}", serviceCard.modelData.name),
                                                        function() { suiteBackend.runEsServiceAction(serviceCard.modelData.unit, "stop") })
                                                }
                                                Button {
                                                    visible: !serviceCard.modelData.actioning
                                                    implicitHeight: 22
                                                    contentItem: Text { text: suiteBackend.uiText("BTN_SERVICES_RESTART"); color: "#4fc3f7"; font.pixelSize: 9 }
                                                    onClicked: window.requestConfirm(
                                                        suiteBackend.uiText("TITLE_SERVICES_CONFIRM_RESTART"),
                                                        suiteBackend.uiText("MSG_SERVICES_CONFIRM_RESTART").replace("{name}", serviceCard.modelData.name),
                                                        function() { suiteBackend.runEsServiceAction(serviceCard.modelData.unit, "restart") })
                                                }
                                            }
                                            Text {
                                                visible: serviceCard.modelData.errorText !== ""
                                                text: serviceCard.modelData.errorText
                                                color: "#e05050"
                                                font.pixelSize: 8
                                                wrapMode: Text.WordWrap
                                                Layout.fillWidth: true
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Text {
                        visible: suiteBackend.esGroups.length === 0
                        text: suiteBackend.uiText("MSG_ES_NONE")
                        color: "#556070"
                        font.pixelSize: 11
                    }
                }
            }
            Text {
                text: suiteBackend.uiText("MSG_ES_NO_CONTROL")
                color: "#556070"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                font.pixelSize: 9
            }
        }
    }

    Component {
        id: ecosystemTelemetryComponent
        ColumnLayout {
            id: telemetryRoot
            width: contentLoader.width
            spacing: 10
            property bool isAggregate: modeCombo.currentIndex === 1

            function runQuery() {
                suiteBackend.runTelemetryQuery(
                    telemetryRoot.isAggregate ? "aggregate" : "query",
                    sourceIdField.text, kindField.text, fieldField.text,
                    startField.text, endField.text, bucketField.text, aggCombo.currentText)
            }

            Text { text: suiteBackend.uiText("HEADING_ECOSYSTEM_TELEMETRY"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            GridLayout {
                columns: 2
                columnSpacing: 8
                rowSpacing: 6
                Text { text: suiteBackend.uiText("LBL_TELEMETRY_MODE"); color: window.muted; font.pixelSize: 10 }
                ComboBox {
                    id: modeCombo
                    Layout.preferredWidth: 200
                    model: [suiteBackend.uiText("TELEMETRY_MODE_QUERY"), suiteBackend.uiText("TELEMETRY_MODE_AGGREGATE")]
                }
                Text { text: suiteBackend.uiText("LBL_TELEMETRY_SOURCE_ID"); color: window.muted; font.pixelSize: 10 }
                TextField { id: sourceIdField; color: window.textPrimary; Layout.preferredWidth: 220; background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder } }
                Text { text: suiteBackend.uiText("LBL_TELEMETRY_KIND"); color: window.muted; font.pixelSize: 10 }
                TextField { id: kindField; color: window.textPrimary; Layout.preferredWidth: 220; background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder } }
                Text { text: suiteBackend.uiText("LBL_TELEMETRY_FIELD"); color: window.muted; font.pixelSize: 10 }
                TextField { id: fieldField; color: window.textPrimary; Layout.preferredWidth: 220; background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder } }
                Text { visible: telemetryRoot.isAggregate; text: suiteBackend.uiText("LBL_TELEMETRY_BUCKET_MS"); color: window.muted; font.pixelSize: 10 }
                TextField { id: bucketField; visible: telemetryRoot.isAggregate; text: "60000"; color: window.textPrimary; Layout.preferredWidth: 120; background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder } }
                Text { visible: telemetryRoot.isAggregate; text: suiteBackend.uiText("LBL_TELEMETRY_AGG"); color: window.muted; font.pixelSize: 10 }
                ComboBox { id: aggCombo; visible: telemetryRoot.isAggregate; model: suiteBackend.telemetryAggregates; Layout.preferredWidth: 120 }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text { text: suiteBackend.uiText("LBL_TELEMETRY_RANGE"); color: window.muted; font.pixelSize: 10 }
                Repeater {
                    model: suiteBackend.telemetryRangePresets
                    delegate: Button {
                        required property var modelData
                        text: modelData.label
                        implicitWidth: 48
                        onClicked: {
                            var now = Date.now()
                            startField.text = String(now - modelData.ms)
                            endField.text = String(now)
                        }
                    }
                }
                TextField { id: startField; placeholderText: suiteBackend.uiText("LBL_TELEMETRY_START"); color: window.textPrimary; Layout.preferredWidth: 140; background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder } }
                TextField { id: endField; placeholderText: suiteBackend.uiText("LBL_TELEMETRY_END"); color: window.textPrimary; Layout.preferredWidth: 140; background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder } }
            }
            RowLayout {
                Button {
                    text: suiteBackend.telemetryRunning ? "..." : suiteBackend.uiText("BTN_RUN_QUERY")
                    enabled: !suiteBackend.telemetryRunning
                    onClicked: telemetryRoot.runQuery()
                }
            }
            Text { text: suiteBackend.telemetryStatusText; color: window.muted; font.pixelSize: 11 }
            RowLayout {
                visible: suiteBackend.telemetryShowStats
                spacing: 8
                EsStatBox { caption: suiteBackend.uiText("LBL_TELEMETRY_STAT_MIN"); value: suiteBackend.telemetryStats.min || "" }
                EsStatBox { caption: suiteBackend.uiText("LBL_TELEMETRY_STAT_MAX"); value: suiteBackend.telemetryStats.max || "" }
                EsStatBox { caption: suiteBackend.uiText("LBL_TELEMETRY_STAT_AVG"); value: suiteBackend.telemetryStats.avg || "" }
                EsStatBox { caption: suiteBackend.uiText("LBL_TELEMETRY_STAT_COUNT"); value: suiteBackend.telemetryStats.count || "" }
            }
            Card {
                Layout.fillWidth: true
                Layout.preferredHeight: 280
                Canvas {
                    id: telemetryCanvas
                    anchors.fill: parent
                    anchors.margins: 12
                    Connections { target: suiteBackend; function onChanged() { telemetryCanvas.requestPaint() } }
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        ctx.strokeStyle = "#1e293b"
                        ctx.lineWidth = 1
                        for (var gy = 0; gy <= 4; gy++) {
                            var y = height * gy / 4
                            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                        }
                        if (suiteBackend.telemetryChartMode === "line") {
                            var pts = suiteBackend.telemetryLinePoints
                            ctx.strokeStyle = "#38bdf8"
                            ctx.lineWidth = 2
                            ctx.beginPath()
                            for (var i = 0; i < pts.length; i++) {
                                var px = pts[i].nx * width
                                var py = height - pts[i].ny * height
                                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py)
                            }
                            ctx.stroke()
                        } else if (suiteBackend.telemetryChartMode === "bar") {
                            var bars = suiteBackend.telemetryBars
                            var slot = width / Math.max(1, bars.length)
                            var barWidth = Math.max(2, slot * 0.6)
                            ctx.fillStyle = "#38bdf8"
                            for (var b = 0; b < bars.length; b++) {
                                var bh = bars[b].nh * height
                                var bx = b * slot + (slot - barWidth) / 2
                                ctx.fillRect(bx, height - bh, barWidth, bh)
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: xyTableComponent
        ColumnLayout {
            id: xyTableRoot
            width: contentLoader.width
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("HEADING_XY_TABLE"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                Button { text: suiteBackend.uiText("BTN_RESET_MODULE"); enabled: suiteBackend.xyCanReset; onClicked: suiteBackend.resetXyTable() }
                ComboBox {
                    id: xyRobotCombo
                    Layout.preferredWidth: 200
                    model: suiteBackend.xyRobotOptions
                    textRole: "label"
                    valueRole: "id"
                    Component.onCompleted: currentIndex = indexOfValue(suiteBackend.xySelectedRobotId)
                    Connections {
                        target: suiteBackend
                        function onChanged() {
                            var idx = xyRobotCombo.indexOfValue(suiteBackend.xySelectedRobotId)
                            if (idx !== xyRobotCombo.currentIndex) xyRobotCombo.currentIndex = idx
                        }
                    }
                    onActivated: suiteBackend.selectXyRobot(currentValue)
                }
            }

            ColumnLayout {
                visible: !suiteBackend.xyHasTable
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 40
                spacing: 8
                Text { text: suiteBackend.uiText("LBL_NO_MODULE_ASSIGNED").replace("{machine}", "XY Table"); color: window.textPrimary; font.bold: true; Layout.alignment: Qt.AlignHCenter }
                Text { text: suiteBackend.uiText("LBL_NO_MODULE_DESC"); color: window.muted; wrapMode: Text.WordWrap; Layout.preferredWidth: 320; horizontalAlignment: Text.AlignHCenter }
                Button { text: suiteBackend.uiText("BTN_ENABLE_MODULE").replace("{machine}", "XY Table"); enabled: suiteBackend.xyHasRobot; onClicked: suiteBackend.enableXyTable(); Layout.alignment: Qt.AlignHCenter }
            }

            ColumnLayout {
                visible: suiteBackend.xyHasTable
                spacing: 10
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 110
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8
                        RowLayout {
                            Text { text: suiteBackend.uiText("GROUP_MODULE_SETTINGS"); color: window.cyan; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                            Button {
                                id: xyRemoveButton
                                text: suiteBackend.uiText("BTN_REMOVE_MODULE")
                                contentItem: Text { text: xyRemoveButton.text; color: "#f43f5e" }
                                onClicked: suiteBackend.disableXyTable()
                            }
                        }
                        RowLayout {
                            spacing: 8
                            Text { text: suiteBackend.uiText("LBL_WIDTH_X"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { id: widthSpin; from: 100; to: 5000; stepSize: 10; value: suiteBackend.xyWidth; editable: true; onValueModified: suiteBackend.setXyWidth(value) }
                            Text { text: suiteBackend.uiText("LBL_LENGTH_Y"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { id: lengthSpin; from: 100; to: 5000; stepSize: 10; value: suiteBackend.xyLength; editable: true; onValueModified: suiteBackend.setXyLength(value) }
                        }
                    }
                }
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8
                        Text { text: suiteBackend.uiText("GROUP_JOG_CONTROL"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                        RowLayout {
                            Text { text: suiteBackend.uiText("LBL_STEP"); color: window.muted; font.pixelSize: 10 }
                            ComboBox {
                                id: stepCombo
                                Layout.preferredWidth: 100
                                model: suiteBackend.xyJogSteps.map(function(s) { return s + " mm" })
                                currentIndex: 4
                                onActivated: suiteBackend.setXyJogStep(suiteBackend.xyJogSteps[currentIndex])
                            }
                        }
                        RowLayout {
                            spacing: 24
                            ColumnLayout {
                                Text { text: "X Axis"; color: window.muted; font.pixelSize: 10 }
                                Text { text: suiteBackend.xyPosX; color: "#f59e0b"; font.family: "Cascadia Mono"; font.pixelSize: 16 }
                                RowLayout {
                                    Button { text: "◀"; onClicked: suiteBackend.jogXyTable("x", -1) }
                                    Button { text: "▶"; onClicked: suiteBackend.jogXyTable("x", 1) }
                                }
                            }
                            ColumnLayout {
                                Text { text: "Y Axis"; color: window.muted; font.pixelSize: 10 }
                                Text { text: suiteBackend.xyPosY; color: "#f59e0b"; font.family: "Cascadia Mono"; font.pixelSize: 16 }
                                RowLayout {
                                    Button { text: "▼"; onClicked: suiteBackend.jogXyTable("y", -1) }
                                    Button { text: "▲"; onClicked: suiteBackend.jogXyTable("y", 1) }
                                }
                            }
                            Item { Layout.fillWidth: true }
                            Button { text: suiteBackend.uiText("BTN_SAVE_CONFIG"); Layout.alignment: Qt.AlignBottom; onClicked: xyTableSaveDialog.open() }
                        }
                    }
                }
            }
            Item { Layout.fillHeight: true }
        }
    }

    // Real decimal-capable SpinBox - QML's own SpinBox works in ints
    // only by default, but the classic panel's QDoubleSpinBox fields
    // here (joint degrees, table mm) are real 2-decimal values -
    // standard Qt Quick fixed-point trick (value stored *100 internally).
    component DecimalSpinBox: SpinBox {
        id: control
        property real realValue: 0
        property real realFrom: 0
        property real realTo: 100
        from: Math.round(realFrom * 100)
        to: Math.round(realTo * 100)
        value: Math.round(realValue * 100)
        stepSize: 100
        editable: true
        signal realValueModified(real value)
        validator: DoubleValidator {
            bottom: Math.min(control.realFrom, control.realTo)
            top: Math.max(control.realFrom, control.realTo)
            decimals: 2
            notation: DoubleValidator.StandardNotation
        }
        textFromValue: function(value, locale) { return Number(value / 100).toLocaleString(locale, "f", 2) }
        valueFromText: function(text, locale) { return Math.round(Number.fromLocaleString(locale, text) * 100) }
        onValueModified: control.realValueModified(control.value / 100)
    }

    Component {
        id: rackGroupComponent
        Card {
            id: rackCard
            required property var modelData
            Layout.preferredWidth: 340
            Layout.preferredHeight: rackColumn.implicitHeight + 28
            ColumnLayout {
                id: rackColumn
                anchors.fill: parent
                anchors.margins: 14
                spacing: 6
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: rackCard.modelData.title; color: window.cyan; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                    Button { text: suiteBackend.uiText("BTN_RESET_MODULE"); implicitHeight: 26; onClicked: suiteBackend.resetRackSystem() }
                }
                RowLayout {
                    Text { text: suiteBackend.uiText("LBL_RACK_TYPE"); color: window.muted; font.pixelSize: 10 }
                    ComboBox {
                        Layout.preferredWidth: 150
                        model: suiteBackend.rackTypeLabels
                        currentIndex: suiteBackend.rackTypeOptions.indexOf(rackCard.modelData.type)
                        onActivated: suiteBackend.setRackType(rackCard.modelData.rackId, suiteBackend.rackTypeOptions[currentIndex])
                    }
                }
                ColumnLayout {
                    visible: rackCard.modelData.active
                    spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: suiteBackend.uiText("LBL_CAPACITY"); color: window.muted; font.pixelSize: 10 }
                        Slider {
                            Layout.fillWidth: true
                            from: 1; to: rackCard.modelData.maxCapacity
                            value: rackCard.modelData.capacity
                            onMoved: suiteBackend.setRackCapacity(rackCard.modelData.rackId, Math.round(value))
                        }
                        Text { text: rackCard.modelData.capacity; color: "#38bdf8"; font.family: "Cascadia Mono"; Layout.preferredWidth: 24 }
                    }
                    Text { text: suiteBackend.uiText("LBL_USABLE_SLOTS"); color: window.muted; font.pixelSize: 10 }
                    GridLayout {
                        columns: 6
                        columnSpacing: 3
                        rowSpacing: 3
                        Repeater {
                            model: rackCard.modelData.slots
                            delegate: Button {
                                required property bool modelData
                                required property int index
                                implicitWidth: 34
                                implicitHeight: 34
                                checkable: true
                                checked: modelData
                                text: (index + 1) + "\n" + (modelData ? "☑" : "☐")
                                font.pixelSize: 8
                                onClicked: suiteBackend.toggleRackSlot(rackCard.modelData.rackId, index)
                            }
                        }
                    }
                    Text { text: suiteBackend.uiText("LBL_BASE_PICKUP_POS"); color: window.muted; font.pixelSize: 10 }
                    GridLayout {
                        columns: 3
                        columnSpacing: 6
                        rowSpacing: 4
                        Repeater {
                            model: ["j1", "j2", "j3", "j4", "j5", "j6"]
                            delegate: ColumnLayout {
                                required property string modelData
                                spacing: 1
                                Text { text: modelData.toUpperCase() + " (°)"; color: window.muted; font.pixelSize: 8 }
                                DecimalSpinBox {
                                    realFrom: -360; realTo: 360
                                    realValue: rackCard.modelData.pos[modelData]
                                    Layout.preferredWidth: 100
                                    onRealValueModified: function(v) { suiteBackend.setRackPos(rackCard.modelData.rackId, modelData, v) }
                                }
                            }
                        }
                    }
                    RowLayout {
                        visible: rackCard.modelData.showTable
                        spacing: 12
                        Repeater {
                            model: ["tx", "ty"]
                            delegate: ColumnLayout {
                                required property string modelData
                                spacing: 1
                                Text { text: "Table " + modelData.substring(1).toUpperCase() + " (mm)"; color: "#d97706"; font.pixelSize: 8 }
                                DecimalSpinBox {
                                    realFrom: -5000; realTo: 5000
                                    realValue: rackCard.modelData.pos[modelData]
                                    Layout.preferredWidth: 100
                                    onRealValueModified: function(v) { suiteBackend.setRackPos(rackCard.modelData.rackId, modelData, v) }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: rackComponent
        ColumnLayout {
            width: contentLoader.width
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("HEADING_RACK_MANAGER"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                ComboBox {
                    id: rackRobotCombo
                    Layout.preferredWidth: 200
                    model: suiteBackend.rackRobotOptions
                    textRole: "label"
                    valueRole: "id"
                    Component.onCompleted: currentIndex = indexOfValue(suiteBackend.rackSelectedRobotId)
                    Connections {
                        target: suiteBackend
                        function onChanged() {
                            var idx = rackRobotCombo.indexOfValue(suiteBackend.rackSelectedRobotId)
                            if (idx !== rackRobotCombo.currentIndex) rackRobotCombo.currentIndex = idx
                        }
                    }
                    onActivated: suiteBackend.selectRackRobot(currentValue)
                }
            }
            ColumnLayout {
                visible: !suiteBackend.rackEnabled
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 40
                spacing: 8
                Text { text: suiteBackend.uiText("LBL_NO_MODULE_ASSIGNED").replace("{machine}", "Rack"); color: window.textPrimary; font.bold: true; Layout.alignment: Qt.AlignHCenter }
                Text { text: suiteBackend.uiText("LBL_NO_MODULE_DESC"); color: window.muted; wrapMode: Text.WordWrap; Layout.preferredWidth: 320; horizontalAlignment: Text.AlignHCenter }
                Button { text: suiteBackend.uiText("BTN_ENABLE_MODULE").replace("{machine}", "Rack"); enabled: suiteBackend.rackHasRobot; onClicked: suiteBackend.enableRackSystem(); Layout.alignment: Qt.AlignHCenter }
            }
            RowLayout {
                visible: suiteBackend.rackEnabled
                Button {
                    id: rackRemoveButton
                    text: suiteBackend.uiText("BTN_REMOVE_MODULE")
                    contentItem: Text { text: rackRemoveButton.text; color: "#f43f5e" }
                    onClicked: suiteBackend.disableRackSystem()
                }
            }
            Flickable {
                visible: suiteBackend.rackEnabled
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: rackRow.implicitWidth
                contentHeight: rackRow.implicitHeight
                clip: true
                RowLayout {
                    id: rackRow
                    spacing: 12
                    Repeater {
                        model: suiteBackend.rackData
                        delegate: rackGroupComponent
                    }
                }
            }
            Item { Layout.fillHeight: true; visible: !suiteBackend.rackEnabled }
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

    Component {
        id: pickAndPlaceComponent
        ColumnLayout {
            width: contentLoader.width
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("HEADING_PICK_AND_PLACE"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                ComboBox {
                    id: pnpMachineCombo
                    Layout.preferredWidth: 190
                    model: suiteBackend.pnpMachineOptions
                    textRole: "label"
                    valueRole: "key"
                    Component.onCompleted: currentIndex = indexOfValue(suiteBackend.pnpMachineType)
                    onActivated: suiteBackend.selectPnpMachine(currentValue)
                }
                Button { text: suiteBackend.uiText("BTN_RESET_MODULE"); enabled: suiteBackend.pnpCanReset; onClicked: suiteBackend.resetPnp() }
                ComboBox {
                    id: pnpRobotCombo
                    Layout.preferredWidth: 200
                    model: suiteBackend.pnpRobotOptions
                    textRole: "label"
                    valueRole: "id"
                    Component.onCompleted: currentIndex = indexOfValue(suiteBackend.pnpSelectedRobotId)
                    Connections {
                        target: suiteBackend
                        function onChanged() {
                            var idx = pnpRobotCombo.indexOfValue(suiteBackend.pnpSelectedRobotId)
                            if (idx !== pnpRobotCombo.currentIndex) pnpRobotCombo.currentIndex = idx
                        }
                    }
                    onActivated: suiteBackend.selectPnpRobot(currentValue)
                }
            }

            ColumnLayout {
                visible: !suiteBackend.pnpEnabled
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 40
                spacing: 8
                Text { text: suiteBackend.uiText("LBL_NO_MODULE_ASSIGNED").replace("{machine}", suiteBackend.pnpMachineLabel); color: window.textPrimary; font.bold: true; Layout.alignment: Qt.AlignHCenter }
                Text { text: suiteBackend.uiText("LBL_NO_MODULE_DESC"); color: window.muted; wrapMode: Text.WordWrap; Layout.preferredWidth: 320; horizontalAlignment: Text.AlignHCenter }
                Button { text: suiteBackend.uiText("BTN_ENABLE_MODULE").replace("{machine}", suiteBackend.pnpMachineLabel); enabled: suiteBackend.pnpHasRobot; onClicked: suiteBackend.enablePnp(); Layout.alignment: Qt.AlignHCenter }
            }

            ColumnLayout {
                visible: suiteBackend.pnpEnabled
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: suiteBackend.uiText("GROUP_MODULE_SETTINGS"); color: window.cyan; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                    Button {
                        id: pnpRemoveButton
                        text: suiteBackend.uiText("BTN_REMOVE_MODULE")
                        contentItem: Text { text: pnpRemoveButton.text; color: "#f43f5e" }
                        onClicked: suiteBackend.disablePnp()
                    }
                }
                Text { text: suiteBackend.uiText("LBL_PNP_POSE_PREVIEW"); color: window.muted; font.pixelSize: 10 }
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: pnpAxisColumn.implicitHeight + 24
                    ColumnLayout {
                        id: pnpAxisColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        Repeater {
                            model: suiteBackend.pnpAxisData
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 8
                                Text { text: modelData.label; color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 120 }
                                Slider {
                                    Layout.fillWidth: true
                                    from: modelData.min; to: modelData.max
                                    value: modelData.value
                                    onMoved: suiteBackend.setPnpAxis(modelData.field, Math.round(value))
                                }
                                SpinBox {
                                    from: modelData.min; to: modelData.max
                                    value: modelData.value
                                    editable: true
                                    Layout.preferredWidth: 150
                                    onValueModified: suiteBackend.setPnpAxis(modelData.field, value)
                                }
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    // Reusable checkable toggle-button grid - same shape as the classic
    // panel's own _build_toggle_group() (Fans/Pumps/Valves), and reused
    // for the Endstops grid too (a different column count, same idea).
    component ToggleGrid: GridLayout {
        property var values: []
        property int columns_: 5
        property var onToggle: function(index) {}
        columns: columns_
        columnSpacing: 4
        rowSpacing: 4
        Repeater {
            model: values
            delegate: Button {
                required property bool modelData
                required property int index
                checkable: true
                checked: modelData
                implicitWidth: 34
                implicitHeight: 30
                text: index + 1
                font.pixelSize: 10
                onClicked: onToggle(index)
            }
        }
    }

    Component {
        id: kinematicBrainStageComponent
        Flickable {
            id: kbsFlick
            width: contentLoader.width
            height: contentLoader.height
            contentWidth: width
            contentHeight: kbsColumn.implicitHeight
            clip: true
            ColumnLayout {
                id: kbsColumn
                width: kbsFlick.width
                spacing: 12
                Text { text: suiteBackend.uiText("HEADING_KINEMATIC_BRAIN_STAGE"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: kbsGantryColumn.implicitHeight + 24
                    ColumnLayout {
                        id: kbsGantryColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8
                        RowLayout {
                            Text { text: suiteBackend.uiText("LBL_GANTRY"); color: window.cyan; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                            Text { text: suiteBackend.uiText("LBL_STEP"); color: window.muted; font.pixelSize: 10 }
                            ComboBox {
                                id: kbsStepCombo
                                Layout.preferredWidth: 100
                                model: suiteBackend.kbsJogSteps.map(function(s) { return s + " mm" })
                                currentIndex: suiteBackend.kbsJogSteps.indexOf(10.0)
                                onActivated: suiteBackend.setKbsJogStep(suiteBackend.kbsJogSteps[currentIndex])
                            }
                        }
                        RowLayout {
                            spacing: 20
                            Repeater {
                                model: suiteBackend.kbsAxisData
                                delegate: ColumnLayout {
                                    required property var modelData
                                    spacing: 2
                                    Text { text: modelData.label; color: window.muted; font.pixelSize: 10; Layout.alignment: Qt.AlignHCenter }
                                    Text { text: modelData.value; color: "#f59e0b"; font.family: "Cascadia Mono"; font.pixelSize: 16; Layout.alignment: Qt.AlignHCenter }
                                    RowLayout {
                                        Layout.alignment: Qt.AlignHCenter
                                        Button { text: "−"; implicitWidth: 30; onClicked: suiteBackend.jogKbsAxis(modelData.axis, -1) }
                                        Button { text: "+"; implicitWidth: 30; onClicked: suiteBackend.jogKbsAxis(modelData.axis, 1) }
                                    }
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }
                        RowLayout {
                            spacing: 8
                            Text { text: suiteBackend.uiText("LBL_WIDTH_X"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { from: 100; to: 5000; value: suiteBackend.kbsTableWidth; editable: true; Layout.preferredWidth: 130; onValueModified: suiteBackend.setKbsTableSize("width", value) }
                            Text { text: suiteBackend.uiText("LBL_LENGTH_Y"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { from: 100; to: 5000; value: suiteBackend.kbsTableLength; editable: true; Layout.preferredWidth: 130; onValueModified: suiteBackend.setKbsTableSize("length", value) }
                            Text { text: suiteBackend.uiText("LBL_HEIGHT_Z"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { from: 10; to: 1000; value: suiteBackend.kbsTableHeight; editable: true; Layout.preferredWidth: 130; onValueModified: suiteBackend.setKbsTableSize("height", value) }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Card {
                        Layout.preferredWidth: 320
                        Layout.preferredHeight: kbsBedColumn.implicitHeight + 24
                        ColumnLayout {
                            id: kbsBedColumn
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6
                            Text { text: suiteBackend.uiText("HEADING_HEATED_BED"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                            RowLayout { Text { text: suiteBackend.uiText("LBL_THERMISTOR_1"); color: window.muted; font.pixelSize: 10; Layout.fillWidth: true } Text { text: suiteBackend.kbsTherm1; color: window.textPrimary; font.family: "Cascadia Mono"; font.pixelSize: 12 } }
                            RowLayout { Text { text: suiteBackend.uiText("LBL_THERMISTOR_2"); color: window.muted; font.pixelSize: 10; Layout.fillWidth: true } Text { text: suiteBackend.kbsTherm2; color: window.textPrimary; font.family: "Cascadia Mono"; font.pixelSize: 12 } }
                            RowLayout {
                                Text { text: suiteBackend.uiText("LBL_TARGET_TEMP"); color: window.muted; font.pixelSize: 10 }
                                SpinBox { from: 0; to: 150; value: suiteBackend.kbsTargetTemp; editable: true; Layout.preferredWidth: 110; onValueModified: suiteBackend.setKbsTargetTemp(value) }
                                Button { text: suiteBackend.kbsSsrOn ? suiteBackend.uiText("BTN_SSR_ON") : suiteBackend.uiText("BTN_SSR_OFF"); onClicked: suiteBackend.toggleKbsSsr() }
                            }
                        }
                    }
                    Card {
                        Layout.preferredWidth: 260
                        Layout.preferredHeight: kbsAtcColumn.implicitHeight + 24
                        ColumnLayout {
                            id: kbsAtcColumn
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6
                            Text { text: suiteBackend.uiText("LBL_ATC_REVOLVER_E0"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                            RowLayout {
                                Button { text: "◀"; implicitWidth: 32; onClicked: suiteBackend.stepKbsAtc(-1) }
                                Text { text: suiteBackend.kbsAtcIndex; color: "#a78bfa"; font.family: "Cascadia Mono"; font.pixelSize: 18; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                                Button { text: "▶"; implicitWidth: 32; onClicked: suiteBackend.stepKbsAtc(1) }
                            }
                            RowLayout {
                                Text { text: suiteBackend.uiText("LBL_TOOL_COUNT"); color: window.muted; font.pixelSize: 10 }
                                SpinBox { from: 2; to: 16; value: suiteBackend.kbsToolCount; editable: true; Layout.preferredWidth: 100; onValueModified: suiteBackend.setKbsToolCount(value) }
                            }
                            Text { text: suiteBackend.kbsHomed ? suiteBackend.uiText("LBL_HOMED") : suiteBackend.uiText("LBL_NOT_HOMED"); color: suiteBackend.kbsHomed ? window.green : window.amber; font.pixelSize: 10 }
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: kbsConveyorRow.implicitHeight + 24
                    RowLayout {
                        id: kbsConveyorRow
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10
                        Text { text: suiteBackend.uiText("LBL_CONVEYOR"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                        Text { text: suiteBackend.uiText("LBL_CONVEYOR_NOT_INSTALLED"); color: window.muted; visible: !suiteBackend.kbsConveyorInstalled; Layout.fillWidth: true }
                        Button { text: suiteBackend.uiText("BTN_MARK_INSTALLED"); visible: !suiteBackend.kbsConveyorInstalled; onClicked: suiteBackend.installKbsConveyor() }
                        Button {
                            visible: suiteBackend.kbsConveyorInstalled
                            text: suiteBackend.kbsConveyorRunning ? suiteBackend.uiText("LBL_RUNNING") : suiteBackend.uiText("LBL_STOPPED")
                            onClicked: suiteBackend.toggleKbsConveyorRun()
                        }
                        Slider {
                            visible: suiteBackend.kbsConveyorInstalled
                            Layout.fillWidth: true
                            from: 0; to: 100
                            value: suiteBackend.kbsConveyorSpeed
                            onMoved: suiteBackend.setKbsConveyorSpeed(Math.round(value))
                        }
                        Text { visible: suiteBackend.kbsConveyorInstalled; text: suiteBackend.kbsConveyorSpeed + "%"; color: window.textPrimary; font.family: "Cascadia Mono"; Layout.preferredWidth: 40 }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: kbsEndstopColumn.implicitHeight + 24
                    ColumnLayout {
                        id: kbsEndstopColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_ENDSTOPS"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                        GridLayout {
                            columns: 6
                            columnSpacing: 6
                            rowSpacing: 6
                            Repeater {
                                model: suiteBackend.kbsEndstopData
                                delegate: Button {
                                    required property var modelData
                                    checkable: true
                                    checked: modelData.active
                                    text: modelData.label
                                    font.pixelSize: 9
                                    onClicked: suiteBackend.toggleKbsEndstop(modelData.key)
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Card {
                        Layout.preferredWidth: 200
                        Layout.preferredHeight: kbsFansColumn.implicitHeight + 24
                        ColumnLayout {
                            id: kbsFansColumn
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6
                            Text { text: suiteBackend.uiText("LBL_FANS"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                            ToggleGrid { values: suiteBackend.kbsFans; columns_: 5; onToggle: function(i) { suiteBackend.toggleKbsFan(i) } }
                        }
                    }
                    Card {
                        Layout.preferredWidth: 220
                        Layout.preferredHeight: kbsPumpsColumn.implicitHeight + 24
                        ColumnLayout {
                            id: kbsPumpsColumn
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6
                            Text { text: suiteBackend.uiText("LBL_PUMPS"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                            ToggleGrid { values: suiteBackend.kbsPumps; columns_: 5; onToggle: function(i) { suiteBackend.toggleKbsPump(i) } }
                        }
                    }
                    Card {
                        Layout.preferredWidth: 220
                        Layout.preferredHeight: kbsValvesColumn.implicitHeight + 24
                        ColumnLayout {
                            id: kbsValvesColumn
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6
                            Text { text: suiteBackend.uiText("LBL_VALVES"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                            ToggleGrid { values: suiteBackend.kbsValves; columns_: 5; onToggle: function(i) { suiteBackend.toggleKbsValve(i) } }
                        }
                    }
                    Item { Layout.fillWidth: true }
                }
                Item { Layout.preferredHeight: 20 }
            }
        }
    }

    // Shared shape behind CNC/Laser/HeatedBed/VacuumTable - mirrors
    // module_config_panel.py's own ModuleConfigPanel exactly (robot
    // selector, enable/disable, width/length, reset), with the two real
    // "extra" shapes (heated_bed/vacuum_table) gated by
    // suiteBackend.moduleExtraKind instead of 4 separate QML files. The
    // right-hand "3D Live View" isn't ported, same real, separate
    // omission as every panel in this family (xy_table/pick_and_place).
    // Reused for all 4 real nav keys via the Loader below.
    Component {
        id: moduleConfigComponent
        ColumnLayout {
            width: contentLoader.width
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText(suiteBackend.moduleHeadingKey); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                Button { text: suiteBackend.uiText("BTN_RESET_MODULE"); enabled: suiteBackend.moduleEnabled; onClicked: suiteBackend.resetModuleConfig() }
                ComboBox {
                    id: moduleRobotCombo
                    Layout.preferredWidth: 200
                    model: suiteBackend.moduleRobotOptions
                    textRole: "label"
                    valueRole: "id"
                    Component.onCompleted: currentIndex = indexOfValue(suiteBackend.moduleSelectedRobotId)
                    Connections {
                        target: suiteBackend
                        function onChanged() {
                            var idx = moduleRobotCombo.indexOfValue(suiteBackend.moduleSelectedRobotId)
                            if (idx !== moduleRobotCombo.currentIndex) moduleRobotCombo.currentIndex = idx
                        }
                    }
                    onActivated: suiteBackend.selectModuleRobot(currentValue)
                }
            }

            ColumnLayout {
                visible: !suiteBackend.moduleEnabled
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 40
                spacing: 8
                Text { text: suiteBackend.uiText("LBL_NO_MODULE_ASSIGNED").replace("{machine}", suiteBackend.moduleMachineName); color: window.textPrimary; font.bold: true; Layout.alignment: Qt.AlignHCenter }
                Text { text: suiteBackend.uiText("LBL_NO_MODULE_DESC"); color: window.muted; wrapMode: Text.WordWrap; Layout.preferredWidth: 320; horizontalAlignment: Text.AlignHCenter }
                Button { text: suiteBackend.uiText("BTN_ENABLE_MODULE").replace("{machine}", suiteBackend.moduleMachineName); enabled: suiteBackend.moduleHasRobot; onClicked: suiteBackend.enableModuleConfig(); Layout.alignment: Qt.AlignHCenter }
            }

            ColumnLayout {
                visible: suiteBackend.moduleEnabled
                spacing: 10
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: moduleSettingsColumn.implicitHeight + 24
                    ColumnLayout {
                        id: moduleSettingsColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8
                        RowLayout {
                            Text { text: suiteBackend.uiText("GROUP_MODULE_SETTINGS"); color: window.cyan; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                            Button {
                                id: moduleRemoveButton
                                text: suiteBackend.uiText("BTN_REMOVE_MODULE")
                                contentItem: Text { text: moduleRemoveButton.text; color: "#f43f5e" }
                                onClicked: suiteBackend.disableModuleConfig()
                            }
                        }
                        RowLayout {
                            spacing: 8
                            Text { text: suiteBackend.uiText("LBL_WIDTH_X"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { from: 10; to: 5000; stepSize: 10; value: suiteBackend.moduleWidth; editable: true; Layout.preferredWidth: 130; onValueModified: suiteBackend.setModuleWidth(value) }
                            Text { text: suiteBackend.uiText("LBL_LENGTH_Y"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { from: 10; to: 5000; stepSize: 10; value: suiteBackend.moduleLength; editable: true; Layout.preferredWidth: 130; onValueModified: suiteBackend.setModuleLength(value) }
                        }
                    }
                }

                Card {
                    visible: suiteBackend.moduleExtraKind === "heated_bed"
                    Layout.fillWidth: true
                    Layout.preferredHeight: heatingColumn.implicitHeight + 24
                    ColumnLayout {
                        id: heatingColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8
                        Text { text: suiteBackend.uiText("GROUP_HEATING_CONTROLS"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                        RowLayout {
                            Text { text: suiteBackend.uiText("LBL_TARGET_TEMP"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { from: 0; to: 300; value: suiteBackend.moduleTargetTemp; editable: true; Layout.preferredWidth: 110; onValueModified: suiteBackend.setModuleTargetTemp(value) }
                            Button { text: suiteBackend.moduleSsrOn ? suiteBackend.uiText("BTN_SSR_ON") : suiteBackend.uiText("BTN_SSR_OFF"); onClicked: suiteBackend.toggleModuleSsr() }
                        }
                        RowLayout {
                            spacing: 20
                            ColumnLayout {
                                spacing: 2
                                Text { text: suiteBackend.uiText("LBL_THERMISTOR_1"); color: window.muted; font.pixelSize: 9 }
                                Text { text: suiteBackend.moduleTherm1; color: "#fb923c"; font.family: "Cascadia Mono"; font.pixelSize: 14 }
                            }
                            ColumnLayout {
                                spacing: 2
                                Text { text: suiteBackend.uiText("LBL_THERMISTOR_2"); color: window.muted; font.pixelSize: 9 }
                                Text { text: suiteBackend.moduleTherm2; color: "#fb923c"; font.family: "Cascadia Mono"; font.pixelSize: 14 }
                            }
                        }
                    }
                }

                Card {
                    visible: suiteBackend.moduleExtraKind === "vacuum_table"
                    Layout.fillWidth: true
                    Layout.preferredHeight: vacuumRow.implicitHeight + 24
                    RowLayout {
                        id: vacuumRow
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10
                        Text { text: suiteBackend.uiText("GROUP_VACUUM_CONTROLS"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                        Button {
                            text: suiteBackend.modulePumpOn ? suiteBackend.uiText("BTN_PUMP_ON") : suiteBackend.uiText("BTN_PUMP_OFF")
                            checkable: true
                            checked: suiteBackend.modulePumpOn
                            onClicked: suiteBackend.toggleModulePump()
                        }
                        Button {
                            text: suiteBackend.moduleValveOn ? suiteBackend.uiText("BTN_VALVE_OPEN") : suiteBackend.uiText("BTN_VALVE_CLOSED")
                            checkable: true
                            checked: suiteBackend.moduleValveOn
                            onClicked: suiteBackend.toggleModuleValve()
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    // Real 6-joint (+ optional table tx/ty) position editor, reused for
    // both a panel slot's own position AND the revolver's base pickup
    // position - mirrors atc_tools_panel.py's own reusable PositionEditor
    // widget. Integer degrees/mm, matching the classic panel's own
    // QSpinBox (not a DecimalSpinBox - ATC positions are whole numbers
    // there too).
    component AtcPosFields: Flow {
        property var fields: []
        property string slotKey: ""
        Layout.fillWidth: true
        spacing: 8
        Repeater {
            model: fields
            delegate: ColumnLayout {
                required property var modelData
                spacing: 1
                Text { text: modelData.label; color: window.muted; font.pixelSize: 8 }
                SpinBox {
                    from: modelData.min; to: modelData.max
                    value: Math.round(modelData.value)
                    editable: true
                    // Real, previously-confirmed bug (see Pick and Place's own
                    // CHANGELOG entry): too narrow a SpinBox clips a real
                    // multi-digit value down to its last digit(s) - table mm
                    // fields need up to 5 digits/sign ("-2000"), so this one
                    // gets extra room over the joint fields' own "-180".
                    Layout.preferredWidth: 150
                    onValueModified: suiteBackend.setAtcPosField(slotKey, modelData.field, value)
                }
            }
        }
    }

    // Real from-scratch 2D graphic (grid of tool slots, or a circular
    // revolver layout) - a hand-drawn QML Canvas mirroring
    // atc_tools_panel.py's own AtcGraphicsWidget (QPainter) 1:1 in
    // structure and color, same "Canvas over a 3D/charting dependency"
    // choice already used by ecosystem_telemetry's own chart.
    Component {
        id: atcGraphicsComponent
        Canvas {
            id: atcCanvas
            function roundRect(ctx, x, y, w, h, r) {
                ctx.beginPath()
                ctx.moveTo(x + r, y)
                ctx.arcTo(x + w, y, x + w, y + h, r)
                ctx.arcTo(x + w, y + h, x, y + h, r)
                ctx.arcTo(x, y + h, x, y, r)
                ctx.arcTo(x, y, x + w, y, r)
                ctx.closePath()
            }
            Connections {
                target: suiteBackend
                function onChanged() { atcCanvas.requestPaint() }
            }
            onPaint: {
                var ctx = getContext("2d")
                ctx.fillStyle = "#0f172a"
                ctx.fillRect(0, 0, width, height)
                var slots = suiteBackend.atcSlotsData
                var hasToolAt = {}
                for (var i = 0; i < slots.length; i++) hasToolAt[slots[i].slot] = slots[i].tool !== "None"

                if (suiteBackend.atcIsPanel) {
                    var parts = suiteBackend.atcPanelGrid.split("x")
                    var rows = Math.max(1, parseInt(parts[0]) || 2)
                    var cols = Math.max(1, parseInt(parts[1]) || 2)
                    var margin = 20
                    var cell = Math.max(1, Math.min((width - margin * 2) / cols, (height - margin * 2) / rows, 90))
                    var gap = Math.max(2, cell / 8)
                    var totalW = cell * cols + gap * (cols - 1)
                    var totalH = cell * rows + gap * (rows - 1)
                    var originX = (width - totalW) / 2
                    var originY = (height - totalH) / 2
                    for (var idx = 0; idx < rows * cols; idx++) {
                        var r = Math.floor(idx / cols), c = idx % cols
                        var x = originX + c * (cell + gap)
                        var y = originY + r * (cell + gap)
                        var hasTool = !!hasToolAt[idx]
                        ctx.lineWidth = 2
                        ctx.strokeStyle = hasTool ? "#0ea5e9" : "#334155"
                        ctx.setLineDash(hasTool ? [] : [4, 3])
                        ctx.fillStyle = hasTool ? "#082f49" : "#0f172a"
                        roundRect(ctx, x, y, cell, cell, 6)
                        ctx.fill(); ctx.stroke()
                        ctx.setLineDash([])
                        ctx.fillStyle = "#64748b"
                        ctx.font = "11px sans-serif"
                        ctx.textAlign = "left"
                        ctx.fillText(String(idx + 1), x, y - 4)
                        if (hasTool) {
                            var dotR = Math.max(4, cell / 6)
                            ctx.fillStyle = "#38bdf8"
                            ctx.beginPath(); ctx.arc(x + cell / 2, y + cell / 2, dotR, 0, Math.PI * 2); ctx.fill()
                        }
                    }
                } else {
                    var slotsN = Math.max(1, suiteBackend.atcRevolverSlots)
                    var radius = Math.max(70, Math.min(width, height) / 2 - 40)
                    var cx = width / 2, cy = height / 2
                    ctx.lineWidth = 4
                    ctx.strokeStyle = "#334155"
                    ctx.setLineDash([])
                    ctx.fillStyle = "#1e293b"
                    ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.fill(); ctx.stroke()
                    var hubR = Math.max(20, radius * 0.18)
                    ctx.fillStyle = "#334155"
                    ctx.beginPath(); ctx.arc(cx, cy, hubR, 0, Math.PI * 2); ctx.fill()
                    for (var s = 0; s < slotsN; s++) {
                        var angle = (s / slotsN) * Math.PI * 2 - Math.PI / 2
                        var sx = cx + Math.cos(angle) * radius
                        var sy = cy + Math.sin(angle) * radius
                        var hasT = !!hasToolAt[s]
                        var slotR = Math.max(14, radius * 0.16)
                        ctx.lineWidth = 2
                        ctx.strokeStyle = hasT ? "#0ea5e9" : "#334155"
                        ctx.setLineDash(hasT ? [] : [4, 3])
                        ctx.fillStyle = hasT ? "#082f49" : "#0f172a"
                        ctx.beginPath(); ctx.arc(sx, sy, slotR, 0, Math.PI * 2); ctx.fill(); ctx.stroke()
                        ctx.setLineDash([])
                        ctx.fillStyle = "#64748b"
                        ctx.font = "10px sans-serif"
                        ctx.textAlign = "center"
                        ctx.fillText(String(s + 1), sx, sy - slotR - 4)
                        if (hasT) {
                            var dR = Math.max(3, slotR * 0.4)
                            ctx.fillStyle = "#38bdf8"
                            ctx.beginPath(); ctx.arc(sx, sy, dR, 0, Math.PI * 2); ctx.fill()
                        }
                    }
                }
            }
        }
    }

    FileDialog {
        id: atcSaveDialog
        title: suiteBackend.uiText("BTN_SAVE_CONFIG")
        fileMode: FileDialog.SaveFile
        nameFilters: ["JSON (*.json)"]
        onAccepted: suiteBackend.saveAtcConfig(selectedFile.toString())
    }
    FileDialog {
        id: atcLoadDialog
        title: suiteBackend.uiText("BTN_LOAD_CONFIG")
        fileMode: FileDialog.OpenFile
        nameFilters: ["JSON (*.json)"]
        onAccepted: suiteBackend.loadAtcConfig(selectedFile.toString())
    }

    Component {
        id: atcComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("HEADING_ATC"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                Button { text: suiteBackend.uiText("BTN_RESET_MODULE"); enabled: suiteBackend.atcConfigured; onClicked: suiteBackend.resetAtc() }
                Button { text: suiteBackend.uiText("BTN_LOAD_CONFIG"); enabled: suiteBackend.atcHasRobot; onClicked: atcLoadDialog.open() }
                Button { text: suiteBackend.uiText("BTN_SAVE_CONFIG"); enabled: suiteBackend.atcHasRobot && suiteBackend.atcConfigured; onClicked: atcSaveDialog.open() }
                ComboBox {
                    id: atcRobotCombo
                    Layout.preferredWidth: 190
                    model: suiteBackend.atcRobotOptions
                    textRole: "label"
                    valueRole: "id"
                    Component.onCompleted: currentIndex = indexOfValue(suiteBackend.atcSelectedRobotId)
                    Connections {
                        target: suiteBackend
                        function onChanged() {
                            var idx = atcRobotCombo.indexOfValue(suiteBackend.atcSelectedRobotId)
                            if (idx !== atcRobotCombo.currentIndex) atcRobotCombo.currentIndex = idx
                        }
                    }
                    onActivated: suiteBackend.selectAtcRobot(currentValue)
                }
            }

            Text { text: suiteBackend.atcLoadError; color: "#ee6b80"; font.pixelSize: 10; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.WordWrap }

            ColumnLayout {
                visible: !suiteBackend.atcConfigured
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 40
                spacing: 8
                Text { text: suiteBackend.uiText("LBL_NO_MODULE_ASSIGNED").replace("{machine}", "ATC"); color: window.textPrimary; font.bold: true; Layout.alignment: Qt.AlignHCenter }
                Text { text: suiteBackend.uiText("LBL_ATC_EMPTY_DESC"); color: window.muted; wrapMode: Text.WordWrap; Layout.preferredWidth: 320; horizontalAlignment: Text.AlignHCenter }
                Button { text: suiteBackend.uiText("BTN_ENABLE_MODULE").replace("{machine}", "ATC"); enabled: suiteBackend.atcHasRobot; onClicked: suiteBackend.enableAtc(); Layout.alignment: Qt.AlignHCenter }
            }

            RowLayout {
                visible: suiteBackend.atcConfigured
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                Flickable {
                    Layout.preferredWidth: contentLoader.width * 0.55
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: atcLeftColumn.implicitHeight
                    clip: true
                    ColumnLayout {
                        id: atcLeftColumn
                        width: parent.width
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            Item { Layout.fillWidth: true }
                            Button {
                                id: atcRemoveButton
                                text: suiteBackend.uiText("BTN_REMOVE_MODULE")
                                contentItem: Text { text: atcRemoveButton.text; color: "#f43f5e" }
                                onClicked: suiteBackend.disableAtc()
                            }
                        }

                        RowLayout {
                            spacing: 6
                            Repeater {
                                model: suiteBackend.atcTypeOptions
                                delegate: Button {
                                    required property var modelData
                                    text: suiteBackend.uiText(modelData.labelKey)
                                    checkable: true
                                    checked: suiteBackend.atcType === modelData.key
                                    onClicked: suiteBackend.setAtcType(modelData.key)
                                }
                            }
                        }

                        Card {
                            visible: suiteBackend.atcIsPanel
                            Layout.fillWidth: true
                            Layout.preferredHeight: 70
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 4
                                Text { text: suiteBackend.uiText("LBL_PANEL_GRID_LAYOUT"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                                ComboBox {
                                    Layout.preferredWidth: 120
                                    model: suiteBackend.atcPanelGridOptions
                                    currentIndex: suiteBackend.atcPanelGridOptions.indexOf(suiteBackend.atcPanelGrid)
                                    onActivated: suiteBackend.setAtcPanelGrid(currentText)
                                }
                            }
                        }

                        Card {
                            visible: !suiteBackend.atcIsPanel
                            Layout.fillWidth: true
                            Layout.preferredHeight: atcRevolverColumn.implicitHeight + 20
                            ColumnLayout {
                                id: atcRevolverColumn
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 6
                                Text { text: suiteBackend.uiText("LBL_REVOLVER_CAPACITY"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                                SpinBox { from: 1; to: 16; value: suiteBackend.atcRevolverSlots; editable: true; Layout.preferredWidth: 110; onValueModified: suiteBackend.setAtcRevolverSlots(value) }
                                RowLayout {
                                    Text { text: suiteBackend.uiText("LBL_BASE_PICKUP_POS"); color: window.muted; font.pixelSize: 10; Layout.fillWidth: true }
                                    Button { text: suiteBackend.uiText("BTN_EDIT_POS"); checkable: true; checked: suiteBackend.atcBaseEditing; onClicked: suiteBackend.toggleAtcBasePos() }
                                }
                                AtcPosFields { visible: suiteBackend.atcBaseEditing; fields: suiteBackend.atcBasePos; slotKey: "revolver" }
                            }
                        }

                        Text { text: suiteBackend.uiText("LBL_TOOL_ASSIGNMENTS"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                        Repeater {
                            model: suiteBackend.atcSlotsData
                            delegate: Card {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: atcSlotColumn.implicitHeight + 16
                                ColumnLayout {
                                    id: atcSlotColumn
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 4
                                    RowLayout {
                                        Text { text: modelData.slot + 1; color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 20 }
                                        ComboBox {
                                            Layout.fillWidth: true
                                            model: suiteBackend.atcToolOptions
                                            currentIndex: modelData.toolIndex
                                            onActivated: suiteBackend.setAtcTool(modelData.slot, currentText)
                                        }
                                        Button {
                                            visible: modelData.showPosButton
                                            text: suiteBackend.uiText("BTN_EDIT_POS")
                                            checkable: true
                                            checked: modelData.editing
                                            onClicked: suiteBackend.toggleAtcSlotPos(modelData.slot)
                                        }
                                    }
                                    AtcPosFields { visible: modelData.editing; fields: modelData.pos; slotKey: String(modelData.slot) }
                                }
                            }
                        }
                        Item { Layout.preferredHeight: 12 }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Loader {
                        anchors.fill: parent
                        anchors.margins: 8
                        sourceComponent: atcGraphicsComponent
                    }
                }
            }
        }
    }

    // Real MJPEG-fed camera grid - mirrors cameras_panel.py's own
    // CamerasPanel/CameraCard 1:1 (real metadata + live feed + PTZ +
    // USB/RTSP discovery, not a placeholder). Each card's own live frame
    // comes from CameraFrameProvider (qt_suite.py) via
    // `image://cameraFrames/<id>/<frameVersion>` - see
    // suiteBackend.cameraFrameVersions's own docstring for why that (and
    // the status badge) is deliberately a SEPARATE, fast-refreshing
    // property from the rest of this card's own config fields.
    Component {
        id: cameraCardComponent
        Card {
            id: camCard
            required property var modelData
            property var frameInfo: {
                var list = suiteBackend.cameraFrameVersions
                for (var i = 0; i < list.length; i++) {
                    if (list[i].id === camCard.modelData.id) return list[i]
                }
                return {version: 0, placeholderText: "", placeholderColor: "#4a5563", statusText: "", statusColor: "#8a97a6"}
            }
            Layout.fillWidth: true
            Layout.preferredHeight: camColumn.implicitHeight + 20
            ColumnLayout {
                id: camColumn
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                RowLayout {
                    Text { text: suiteBackend.uiText("LBL_CAM") + " " + camCard.modelData.id; color: window.textPrimary; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                    Text { text: camCard.frameInfo.statusText; color: camCard.frameInfo.statusColor; font.pixelSize: 9; font.bold: true }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 140
                    Image {
                        id: videoImage
                        anchors.fill: parent
                        visible: camCard.frameInfo.placeholderText === "" && camCard.frameInfo.version > 0
                        fillMode: Image.PreserveAspectFit
                        cache: false
                        asynchronous: true
                        source: camCard.frameInfo.version > 0 ? ("image://cameraFrames/" + camCard.modelData.id + "/" + camCard.frameInfo.version) : ""
                    }
                    Rectangle {
                        anchors.fill: parent
                        visible: !videoImage.visible
                        color: "#0a0f14"
                        border.width: 1
                        border.color: "#1a2530"
                        Text {
                            anchors.centerIn: parent
                            text: camCard.frameInfo.placeholderText
                            color: camCard.frameInfo.placeholderColor
                            font.bold: true
                            font.pixelSize: 11
                        }
                    }
                }

                Button {
                    id: ptzToggleBtn
                    visible: camCard.modelData.isIp
                    text: suiteBackend.uiText("BTN_PTZ_TOGGLE")
                    checkable: true
                    Layout.fillWidth: true
                }
                RowLayout {
                    visible: ptzToggleBtn.checked && camCard.modelData.isIp
                    spacing: 3
                    Repeater {
                        model: [
                            {label: "◀", pan: -60, tilt: 0, zoom: 0},
                            {label: "▲", pan: 0, tilt: 60, zoom: 0},
                            {label: "▼", pan: 0, tilt: -60, zoom: 0},
                            {label: "▶", pan: 60, tilt: 0, zoom: 0},
                            {label: "+", pan: 0, tilt: 0, zoom: 60},
                            {label: "−", pan: 0, tilt: 0, zoom: -60}
                        ]
                        delegate: Button {
                            required property var modelData
                            text: modelData.label
                            Layout.fillWidth: true
                            onPressed: suiteBackend.sendCameraPtz(camCard.modelData.id, modelData.pan, modelData.tilt, modelData.zoom)
                            onReleased: suiteBackend.sendCameraPtz(camCard.modelData.id, 0, 0, 0)
                        }
                    }
                }
                Text {
                    visible: ptzToggleBtn.checked && camCard.modelData.ptzError.length > 0
                    text: camCard.modelData.ptzError
                    color: "#ef4444"
                    font.pixelSize: 8
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                ComboBox {
                    Layout.fillWidth: true
                    model: camCard.modelData.typeOptions
                    currentIndex: camCard.modelData.typeIndex
                    onActivated: suiteBackend.setCameraType(camCard.modelData.id, currentText)
                }

                RowLayout {
                    Text { text: suiteBackend.uiText("LBL_ASSIGNED_ROBOT"); color: window.muted; font.pixelSize: 9 }
                    ComboBox {
                        Layout.fillWidth: true
                        model: suiteBackend.cameraRobotOptions
                        textRole: "label"
                        valueRole: "id"
                        Component.onCompleted: currentIndex = indexOfValue(camCard.modelData.assignedRobotId)
                        onActivated: suiteBackend.setCameraAssignedRobot(camCard.modelData.id, currentValue)
                    }
                }

                RowLayout {
                    spacing: 4
                    Button { text: suiteBackend.uiText("BTN_SOURCE_USB"); checkable: true; checked: !camCard.modelData.isIp; Layout.fillWidth: true; onClicked: suiteBackend.setCameraSourceType(camCard.modelData.id, "usb") }
                    Button { text: suiteBackend.uiText("BTN_SOURCE_IP"); checkable: true; checked: camCard.modelData.isIp; Layout.fillWidth: true; onClicked: suiteBackend.setCameraSourceType(camCard.modelData.id, "ip") }
                }

                ColumnLayout {
                    visible: !camCard.modelData.isIp
                    Layout.fillWidth: true
                    spacing: 3
                    Text { text: suiteBackend.uiText("LBL_HARDWARE_SOURCE"); color: window.muted; font.pixelSize: 9 }
                    TextField {
                        Layout.fillWidth: true
                        text: camCard.modelData.hardwareSource
                        placeholderText: "/dev/video0"
                        onEditingFinished: suiteBackend.setCameraField(camCard.modelData.id, "hardware_source", text)
                    }
                    Button {
                        text: suiteBackend.uiText("BTN_DISCOVER_USB")
                        Layout.fillWidth: true
                        onClicked: suiteBackend.discoverUsbDevices(camCard.modelData.id)
                    }
                    ComboBox {
                        Layout.fillWidth: true
                        visible: camCard.modelData.usbDevices.length > 0
                        model: camCard.modelData.usbDevices
                        textRole: "label"
                        valueRole: "value"
                        onActivated: suiteBackend.pickUsbDevice(camCard.modelData.id, currentValue)
                    }
                }

                ColumnLayout {
                    visible: camCard.modelData.isIp
                    Layout.fillWidth: true
                    spacing: 3
                    Text { text: suiteBackend.uiText("LBL_IP_HOST"); color: window.muted; font.pixelSize: 9 }
                    TextField {
                        id: ipHostField
                        Layout.fillWidth: true
                        text: camCard.modelData.ipHost
                        placeholderText: "192.168.0.210"
                        onEditingFinished: suiteBackend.setCameraField(camCard.modelData.id, "ip_host", text)
                    }
                    RowLayout {
                        ColumnLayout {
                            Text { text: suiteBackend.uiText("LBL_RTSP_PORT"); color: window.muted; font.pixelSize: 9 }
                            SpinBox {
                                id: rtspPortSpin
                                from: 1; to: 65535
                                value: camCard.modelData.rtspPort
                                editable: true
                                Layout.preferredWidth: 130
                                onValueModified: suiteBackend.setCameraField(camCard.modelData.id, "rtsp_port", value)
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: suiteBackend.uiText("LBL_RTSP_PATH"); color: window.muted; font.pixelSize: 9 }
                            TextField {
                                Layout.fillWidth: true
                                text: camCard.modelData.rtspPath
                                placeholderText: "/11"
                                onEditingFinished: suiteBackend.setCameraField(camCard.modelData.id, "rtsp_path", text)
                            }
                        }
                    }
                    Button {
                        text: suiteBackend.uiText("BTN_DISCOVER_RTSP")
                        Layout.fillWidth: true
                        onClicked: suiteBackend.discoverRtspPath(camCard.modelData.id, ipHostField.text, rtspPortSpin.value, ipUserField.text, ipPassField.text)
                    }
                    Repeater {
                        model: camCard.modelData.extraPaths
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Text { text: modelData.label; color: window.muted; font.pixelSize: 9 }
                            TextField {
                                Layout.fillWidth: true
                                text: modelData.value
                                onEditingFinished: suiteBackend.setCameraExtraPath(camCard.modelData.id, modelData.index, text)
                            }
                        }
                    }
                    RowLayout {
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: suiteBackend.uiText("LBL_IP_USERNAME"); color: window.muted; font.pixelSize: 9 }
                            TextField {
                                id: ipUserField
                                Layout.fillWidth: true
                                text: camCard.modelData.ipUsername
                                placeholderText: "admin"
                                onEditingFinished: suiteBackend.setCameraField(camCard.modelData.id, "ip_username", text)
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: suiteBackend.uiText("LBL_IP_PASSWORD"); color: window.muted; font.pixelSize: 9 }
                            TextField {
                                id: ipPassField
                                Layout.fillWidth: true
                                echoMode: TextInput.Password
                                text: camCard.modelData.ipPassword
                                onEditingFinished: suiteBackend.setCameraField(camCard.modelData.id, "ip_password", text)
                            }
                        }
                    }
                }

                Text {
                    visible: camCard.modelData.discoveryStatusText.length > 0
                    text: camCard.modelData.discoveryStatusText
                    color: camCard.modelData.discoveryStatusColor
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Button {
                    Layout.fillWidth: true
                    text: suiteBackend.uiText("BTN_TOGGLE_CONNECTION") + " (" + (camCard.modelData.connected ? suiteBackend.uiText("STATUS_CONNECTED") : suiteBackend.uiText("STATUS_DISCONNECTED")) + ")"
                    onClicked: suiteBackend.toggleCameraConnection(camCard.modelData.id)
                }
            }
        }
    }

    Component {
        id: camerasComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 10
            Text { text: suiteBackend.uiText("TAB_CAMERAS"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: camGrid.implicitHeight
                clip: true
                GridLayout {
                    id: camGrid
                    width: parent.width
                    columns: 4
                    columnSpacing: 8
                    rowSpacing: 8
                    Repeater {
                        model: suiteBackend.camerasData
                        delegate: cameraCardComponent
                    }
                }
            }
        }
    }

    FileDialog {
        id: flasherBrowseDialog
        title: suiteBackend.uiText("BTN_BROWSE_BIN")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Binary (*.bin)"]
        onAccepted: suiteBackend.browseFlasherFile(selectedFile.toString())
    }

    // Real CAN-OTA (and, for the Kinematic Brain, SPI-OTA) firmware
    // flasher - mirrors flasher_panel.py's own FlasherPanel 1:1 (mock
    // simulation client-side, a real hardware path for kinematicBrain/
    // controllerBoard). NOT an embed of the separate URTC-FLASHER app -
    // this panel's own real logic lives in can_ota.py, imported directly,
    // same as every other panel in this shell. Reused for both real nav
    // keys (`urtc_flasher`/`hydra_flasher`) via _FLASHER_TIERS in
    // qt_suite.py, same generic-over-nav-key shape as the Module Config
    // family.
    Component {
        id: flasherComponent
        Flickable {
            id: flasherFlick
            width: contentLoader.width
            height: contentLoader.height
            contentWidth: width
            contentHeight: flasherColumn.implicitHeight
            clip: true
            ColumnLayout {
                id: flasherColumn
                width: flasherFlick.width
                spacing: 10

                Text { text: suiteBackend.uiText("HEADING_FLASHER"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Text { text: suiteBackend.uiText("LBL_HARDWARE_TARGET_UNREACHABLE"); color: window.amber; visible: suiteBackend.flasherUnreachable; Layout.fillWidth: true; wrapMode: Text.WordWrap }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: flasherTargetColumn.implicitHeight + 20
                    ColumnLayout {
                        id: flasherTargetColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        RowLayout {
                            Text { text: suiteBackend.uiText("LBL_BOARD"); color: window.muted; font.pixelSize: 10 }
                            ComboBox {
                                id: flasherTierCombo
                                Layout.fillWidth: true
                                model: suiteBackend.flasherTierOptions
                                textRole: "label"
                                valueRole: "key"
                                Component.onCompleted: currentIndex = indexOfValue(suiteBackend.flasherTier)
                                Connections {
                                    target: suiteBackend
                                    function onChanged() {
                                        var idx = flasherTierCombo.indexOfValue(suiteBackend.flasherTier)
                                        if (idx !== flasherTierCombo.currentIndex) flasherTierCombo.currentIndex = idx
                                    }
                                }
                                onActivated: suiteBackend.selectFlasherTier(currentValue)
                            }
                        }
                        RowLayout {
                            visible: suiteBackend.flasherNeedsRobotSlot
                            Text { text: suiteBackend.uiText("LBL_ROBOT_SLOT"); color: window.muted; font.pixelSize: 10 }
                            ComboBox {
                                id: flasherRobotCombo
                                Layout.fillWidth: true
                                model: suiteBackend.flasherRobotOptions
                                textRole: "label"
                                valueRole: "id"
                                Component.onCompleted: currentIndex = indexOfValue(suiteBackend.flasherSelectedRobotId)
                                Connections {
                                    target: suiteBackend
                                    function onChanged() {
                                        var idx = flasherRobotCombo.indexOfValue(suiteBackend.flasherSelectedRobotId)
                                        if (idx !== flasherRobotCombo.currentIndex) flasherRobotCombo.currentIndex = idx
                                    }
                                }
                                onActivated: suiteBackend.selectFlasherRobot(currentValue)
                            }
                        }
                        Text { text: suiteBackend.flasherHopDescription; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        RowLayout {
                            Text { text: suiteBackend.flasherVersionLabel; color: window.textPrimary; font.pixelSize: 10; Layout.fillWidth: true }
                            Button {
                                text: suiteBackend.flasherQueryBusy ? "..." : suiteBackend.uiText("BTN_QUERY_VERSION")
                                enabled: !suiteBackend.flasherQueryBusy
                                onClicked: suiteBackend.flasherQueryVersion()
                            }
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: flasherFileColumn.implicitHeight + 20
                    ColumnLayout {
                        id: flasherFileColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_FIRMWARE_FILE"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                        RowLayout {
                            Button { text: suiteBackend.uiText("BTN_BROWSE_BIN"); Layout.fillWidth: true; onClicked: flasherBrowseDialog.open() }
                            Button {
                                visible: suiteBackend.flasherGithubAvailable
                                text: suiteBackend.flasherGithubBusy ? "..." : suiteBackend.flasherGithubButtonLabel
                                enabled: !suiteBackend.flasherGithubBusy
                                Layout.fillWidth: true
                                onClicked: suiteBackend.fetchFlasherGithub()
                            }
                        }
                        Text { text: suiteBackend.flasherFileInfo; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                        ColumnLayout {
                            visible: suiteBackend.flasherGithubAssets.length > 0
                            Layout.fillWidth: true
                            Layout.maximumHeight: 120
                            spacing: 2
                            Repeater {
                                model: suiteBackend.flasherGithubAssets
                                delegate: Text {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    color: window.textPrimary
                                    font.pixelSize: 9
                                    MouseArea { anchors.fill: parent; onClicked: suiteBackend.useFlasherGithubAsset(modelData.index) }
                                }
                            }
                        }
                        RowLayout {
                            spacing: 16
                            // A plain, text-less CheckBox + an independent sibling
                            // Text, rather than CheckBox's own `text`/`contentItem` -
                            // the Basic style's own default label color barely shows
                            // against this app's dark background, and a partial
                            // `contentItem` override left the real indicator glyph
                            // overlapping the label (a real, confirmed bug caught by
                            // this control's own on-screen screenshot - two
                            // independent RowLayout siblings sidesteps the whole
                            // indicator/contentItem layout interaction instead).
                            RowLayout {
                                spacing: 6
                                CheckBox { id: allowDowngradeCheck; checked: suiteBackend.flasherAllowDowngrade; onToggled: suiteBackend.setFlasherAllowDowngrade(checked) }
                                Text {
                                    text: suiteBackend.uiText("LBL_ALLOW_DOWNGRADE")
                                    color: window.muted
                                    MouseArea { anchors.fill: parent; onClicked: allowDowngradeCheck.toggle() }
                                }
                            }
                            RowLayout {
                                spacing: 6
                                CheckBox { id: eraseFramCheck; checked: suiteBackend.flasherEraseFram; onToggled: suiteBackend.setFlasherEraseFram(checked) }
                                Text {
                                    text: suiteBackend.uiText("LBL_ERASE_FRAM")
                                    color: window.muted
                                    MouseArea { anchors.fill: parent; onClicked: eraseFramCheck.toggle() }
                                }
                            }
                        }
                    }
                }

                Button {
                    Layout.fillWidth: true
                    text: suiteBackend.uiText("BTN_FLASH_NOW")
                    enabled: suiteBackend.flasherCanFlash
                    onClicked: window.requestConfirm(suiteBackend.uiText("BTN_FLASH_NOW"), suiteBackend.flasherConfirmMessage, function() { suiteBackend.startFlasherFlash() })
                }
                Text { text: suiteBackend.flasherProgressLabel; color: window.muted; font.pixelSize: 10; visible: text.length > 0 }
                ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: suiteBackend.flasherProgressPercent }

                Text { text: suiteBackend.uiText("LBL_LOG_TITLE"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    Flickable {
                        id: flasherLogFlick
                        anchors.fill: parent
                        anchors.margins: 8
                        contentWidth: width
                        contentHeight: flasherLogColumn.implicitHeight
                        clip: true
                        onContentHeightChanged: contentY = Math.max(0, contentHeight - height)
                        ColumnLayout {
                            id: flasherLogColumn
                            width: flasherLogFlick.width
                            spacing: 1
                            Repeater {
                                model: suiteBackend.flasherLog
                                delegate: Text {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: modelData.text
                                    color: modelData.level === "error" ? "#fb7185" : (modelData.level === "ok" ? "#34d399" : "#94a3b8")
                                    font.family: "Cascadia Mono"
                                    font.pixelSize: 9
                                    wrapMode: Text.WrapAnywhere
                                }
                            }
                        }
                    }
                }
                Item { Layout.preferredHeight: 12 }
            }
        }
    }

    ColorDialog {
        id: testerColorDialog
        title: suiteBackend.uiText("LBL_STATUS_LED")
        onAccepted: suiteBackend.setTesterStatusColor(selectedColor.toString())
    }

    // Real CAN-OTA runtime diagnostics - mirrors tester_panel.py's own
    // TesterPanel 1:1: global LED/OLED/F-RAM controls, per-tool
    // telemetry, safe self-test, raw CAN bus monitor. Deliberately
    // duplicates flasherComponent's own target-selection block rather
    // than sharing it, matching that file's own header on why (STUDIO's
    // own Tester.tsx/Flasher.tsx do the same real duplication). Reused
    // for both real nav keys (`urtc_tester`/`hydra_tester`) via
    // _TESTER_TIERS in qt_suite.py.
    Component {
        id: testerComponent
        Flickable {
            id: testerFlick
            width: contentLoader.width
            height: contentLoader.height
            contentWidth: width
            contentHeight: testerColumn.implicitHeight
            clip: true
            ColumnLayout {
                id: testerColumn
                width: testerFlick.width
                spacing: 10

                Text { text: suiteBackend.uiText("HEADING_TESTER"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Text { text: suiteBackend.uiText("LBL_TESTER_SIMULATED_NOTE"); color: window.amber; visible: suiteBackend.testerSimulatedNoteVisible; Layout.fillWidth: true; wrapMode: Text.WordWrap }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: testerTargetColumn.implicitHeight + 20
                    ColumnLayout {
                        id: testerTargetColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        RowLayout {
                            Text { text: suiteBackend.uiText("LBL_BOARD"); color: window.muted; font.pixelSize: 10 }
                            ComboBox {
                                id: testerTierCombo
                                Layout.fillWidth: true
                                model: suiteBackend.testerTierOptions
                                textRole: "label"
                                valueRole: "key"
                                Component.onCompleted: currentIndex = indexOfValue(suiteBackend.testerTier)
                                Connections {
                                    target: suiteBackend
                                    function onChanged() {
                                        var idx = testerTierCombo.indexOfValue(suiteBackend.testerTier)
                                        if (idx !== testerTierCombo.currentIndex) testerTierCombo.currentIndex = idx
                                    }
                                }
                                onActivated: suiteBackend.selectTesterTier(currentValue)
                            }
                        }
                        RowLayout {
                            visible: suiteBackend.testerNeedsRobotSlot
                            Text { text: suiteBackend.uiText("LBL_ROBOT_SLOT"); color: window.muted; font.pixelSize: 10 }
                            ComboBox {
                                id: testerRobotCombo
                                Layout.fillWidth: true
                                model: suiteBackend.testerRobotOptions
                                textRole: "label"
                                valueRole: "id"
                                Component.onCompleted: currentIndex = indexOfValue(suiteBackend.testerSelectedRobotId)
                                Connections {
                                    target: suiteBackend
                                    function onChanged() {
                                        var idx = testerRobotCombo.indexOfValue(suiteBackend.testerSelectedRobotId)
                                        if (idx !== testerRobotCombo.currentIndex) testerRobotCombo.currentIndex = idx
                                    }
                                }
                                onActivated: suiteBackend.selectTesterRobot(currentValue)
                            }
                        }
                        Text { text: suiteBackend.testerHopDescription; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        RowLayout {
                            Text { text: suiteBackend.testerVersionLabel; color: window.textPrimary; font.pixelSize: 10; Layout.fillWidth: true }
                            Button { text: suiteBackend.uiText("BTN_QUERY_VERSION"); enabled: suiteBackend.testerQueryEnabled; onClicked: suiteBackend.testerQueryVersion() }
                        }
                    }
                }

                Card {
                    visible: suiteBackend.testerShowGlobal
                    Layout.fillWidth: true
                    Layout.preferredHeight: testerGlobalColumn.implicitHeight + 20
                    ColumnLayout {
                        id: testerGlobalColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_GLOBAL_CONTROLS"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                        RowLayout {
                            Text { text: suiteBackend.uiText("LBL_STATUS_LED"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 100 }
                            Rectangle {
                                width: 60; height: 26; radius: 4
                                color: suiteBackend.testerStatusColor
                                border.width: 1; border.color: window.panelBorder
                                MouseArea { anchors.fill: parent; onClicked: { testerColorDialog.selectedColor = suiteBackend.testerStatusColor; testerColorDialog.open() } }
                            }
                        }
                        RowLayout {
                            Text { text: suiteBackend.uiText("LBL_RING_LED"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 100 }
                            Button { text: suiteBackend.testerRingOn ? suiteBackend.uiText("LBL_ON") : suiteBackend.uiText("LBL_OFF"); onClicked: suiteBackend.toggleTesterRing() }
                        }
                        RowLayout {
                            Text { text: suiteBackend.uiText("LBL_OLED_MODE"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 100 }
                            ComboBox {
                                Layout.preferredWidth: 140
                                model: [suiteBackend.uiText("LBL_OLED_STANDARD"), suiteBackend.uiText("LBL_OLED_NIGHT"), suiteBackend.uiText("LBL_OLED_OFF")]
                                property var modes: ["standard", "night", "off"]
                                currentIndex: modes.indexOf(suiteBackend.testerOledMode)
                                onActivated: suiteBackend.setTesterOledMode(modes[currentIndex])
                            }
                        }
                        Text { text: suiteBackend.testerExpansionLabel; color: window.muted; font.pixelSize: 9; visible: text.length > 0 }
                    }
                }

                Card {
                    visible: suiteBackend.testerShowFram
                    Layout.fillWidth: true
                    Layout.preferredHeight: testerFramColumn.implicitHeight + 20
                    ColumnLayout {
                        id: testerFramColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_FRAM"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                        Text { text: suiteBackend.testerFramStateLabel; color: window.textPrimary; font.pixelSize: 10 }
                        RowLayout {
                            Button { text: suiteBackend.uiText("BTN_FRAM_QUERY"); onClicked: suiteBackend.testerFramQuery() }
                            Button { text: suiteBackend.uiText("BTN_FRAM_ERASE"); onClicked: suiteBackend.testerFramErase() }
                        }
                    }
                }

                Card {
                    visible: suiteBackend.testerShowTelemetry
                    Layout.fillWidth: true
                    Layout.preferredHeight: testerTelemetryColumn.implicitHeight + 20
                    ColumnLayout {
                        id: testerTelemetryColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4
                        Text { text: suiteBackend.testerTelemetryTitle; color: window.cyan; font.bold: true; font.pixelSize: 11 }
                        Text { text: suiteBackend.testerTelemetryLabel; color: window.muted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                }

                Text { text: suiteBackend.uiText("LBL_SELF_TEST"); color: window.cyan; font.bold: true; font.pixelSize: 11 }
                RowLayout {
                    Text { text: suiteBackend.uiText("LBL_SELF_TEST_NOTE"); color: window.muted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Button {
                        text: suiteBackend.testerTesting ? "..." : suiteBackend.uiText("BTN_RUN_SELF_TEST")
                        enabled: suiteBackend.testerQueryEnabled && !suiteBackend.testerTesting
                        onClicked: suiteBackend.runTesterSelfTest()
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Repeater {
                        model: suiteBackend.testerSelfTestSteps
                        delegate: Text {
                            required property var modelData
                            text: (modelData.passed ? "✅ " : "❌ ") + modelData.label
                            color: modelData.passed ? "#34d399" : "#fb7185"
                            font.pixelSize: 10
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: suiteBackend.uiText("LBL_BUS_MONITOR"); color: window.cyan; font.bold: true; font.pixelSize: 11; Layout.fillWidth: true }
                    Button {
                        text: suiteBackend.testerMonitorRunning ? suiteBackend.uiText("BTN_MONITOR_STOP") : suiteBackend.uiText("BTN_MONITOR_START")
                        enabled: suiteBackend.testerQueryEnabled || suiteBackend.testerMonitorRunning
                        onClicked: suiteBackend.toggleTesterMonitor()
                    }
                }
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 4
                        RowLayout {
                            Text { text: suiteBackend.uiText("LBL_COL_TIME"); color: window.muted; font.pixelSize: 9; Layout.preferredWidth: 80 }
                            Text { text: suiteBackend.uiText("LBL_COL_ID"); color: window.muted; font.pixelSize: 9; Layout.preferredWidth: 70 }
                            Text { text: "DLC"; color: window.muted; font.pixelSize: 9; Layout.preferredWidth: 40 }
                            Text { text: suiteBackend.uiText("LBL_COL_DATA"); color: window.muted; font.pixelSize: 9; Layout.fillWidth: true }
                        }
                        Flickable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            contentWidth: width
                            contentHeight: testerFramesColumn.implicitHeight
                            clip: true
                            ColumnLayout {
                                id: testerFramesColumn
                                width: parent.width
                                spacing: 1
                                Repeater {
                                    model: suiteBackend.testerFrames
                                    delegate: RowLayout {
                                        required property var modelData
                                        Text { text: modelData.time; color: window.textPrimary; font.family: "Cascadia Mono"; font.pixelSize: 9; Layout.preferredWidth: 80 }
                                        Text { text: modelData.id; color: "#38bdf8"; font.family: "Cascadia Mono"; font.pixelSize: 9; Layout.preferredWidth: 70 }
                                        Text { text: modelData.dlc; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 9; Layout.preferredWidth: 40 }
                                        Text { text: modelData.data; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 9; Layout.fillWidth: true }
                                    }
                                }
                            }
                        }
                    }
                }
                Item { Layout.preferredHeight: 12 }
            }
        }
    }

    // Real live 3D robot viewport - orbit camera (left-drag rotate, wheel
    // zoom, right/middle-drag pan), any of the 24 real STL-backed models
    // plus the primitive-built "Generic" fallback, matching
    // viewport_panel.py's own ViewportPanel/RobotViewport 1:1. The one
    // real 3D panel in this whole shell - see
    // render/viewport.py's own OffscreenRobotRenderer for why this is a
    // genuinely separate QOpenGLContext/FBO rather than Qt Quick 3D or
    // QQuickFramebufferObject (both would force this app's whole Quick
    // backend off Windows' own real default, Direct3D11). Reuses the
    // SAME real robot selection Robot Control/Trajectory already share -
    // no separate combo box here, matching the classic panel's own real
    // behavior (it also just follows whichever robot is selected
    // elsewhere, via set_selected_robot()).
    Component {
        id: viewportComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 8
            Text { text: suiteBackend.uiText("HEADING_VIEWPORT"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }

            Item {
                id: viewportArea
                Layout.fillWidth: true
                Layout.fillHeight: true

                Image {
                    id: viewportImage
                    anchors.fill: parent
                    visible: suiteBackend.viewportHasRobot && suiteBackend.viewportSupported
                    fillMode: Image.Stretch
                    cache: false
                    asynchronous: true
                    source: visible ? ("image://viewportFrame/" + suiteBackend.viewportFrameVersion) : ""

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                        property real lastX: 0
                        property real lastY: 0
                        onPressed: function(mouse) { lastX = mouse.x; lastY = mouse.y }
                        onPositionChanged: function(mouse) {
                            var dx = mouse.x - lastX
                            var dy = mouse.y - lastY
                            lastX = mouse.x
                            lastY = mouse.y
                            if (mouse.buttons & Qt.LeftButton) {
                                suiteBackend.viewportOrbit(dx, dy)
                            } else if (mouse.buttons & (Qt.RightButton | Qt.MiddleButton)) {
                                suiteBackend.viewportPan(dx, dy)
                            }
                        }
                        onWheel: function(wheel) {
                            suiteBackend.viewportZoom(wheel.angleDelta.y > 0 ? 0.9 : 1.1)
                        }
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    visible: !viewportImage.visible
                    color: "#0a0f14"
                    border.width: 1
                    border.color: "#1a2530"
                    Text {
                        anchors.centerIn: parent
                        anchors.margins: 20
                        width: parent.width - 40
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        text: suiteBackend.viewportUnsupportedMessage
                        color: window.muted
                    }
                }

                onWidthChanged: if (viewportImage.visible) suiteBackend.viewportResize(width, height)
                onHeightChanged: if (viewportImage.visible) suiteBackend.viewportResize(width, height)
            }

            Text { text: suiteBackend.uiText("HINT_CONTROLS"); color: "#4a5563"; font.pixelSize: 10 }
        }
    }
}
