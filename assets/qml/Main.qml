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
