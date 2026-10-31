// =============================================================================
// HYDRA-UMC SUITE - Qt Quick command deck shell
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
//
// The one interface of HYDRA-UMC SUITE: a navigation sidebar and a single
// content area, bridged to Python by qt_suite.py. Same dark navy/cyan
// "command deck" look as HYDRA-UMC-OS-REBUILDER, HYDRA-UMC-UPDATER,
// URTC-TESTER and URTC-FLASHER, for ecosystem-wide visual consistency.
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

    // Closing the window first sends the writes that are waiting and closes the connections, then quits.
    onClosing: function(close) {
        if (!suiteBackend.shutdownDone) {
            close.accepted = false
            suiteBackend.shutdownAndQuit()
        }
    }

    // Documented single shortcut of the global STOP (Help/README): a bare
    // function key, application-wide, so it works on every panel; it does not
    // press a focused button (unlike Space) and closes nothing (unlike Esc).
    Shortcut {
        sequence: "F12"
        context: Qt.ApplicationShortcut
        autoRepeat: false
        onActivated: suiteBackend.stopAll()
    }

    // F11 toggles real full screen (the window starts maximized, with its native title bar).
    Shortcut {
        sequence: "F11"
        context: Qt.ApplicationShortcut
        autoRepeat: false
        onActivated: window.visibility = (window.visibility === Window.FullScreen ? Window.Maximized : Window.FullScreen)
    }

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
    property string pendingConfirmLabel: ""

    // label is optional: the button says "Save" unless the caller names what it confirms.
    function requestConfirm(title, body, action, label) {
        pendingConfirmTitle = title
        pendingConfirmBody = body
        pendingConfirmAction = action
        pendingConfirmLabel = label ? label : ""
        confirmDialog.open()
    }

    function openCredentials(connId) {
        var creds = suiteBackend.serverCredentials(connId)
        window.credentialsConnId = connId
        credentialsUsernameField.text = creds.username
        credentialsPasswordField.text = creds.password
        credentialsRememberBox.checked = creds.remember
        credentialsCodeField.text = ""
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

    // One nav leaf (a panel to show) or category (drills into a submenu).
    component NavButton: Rectangle {
        id: navBtn
        property string label: ""
        property bool active: false
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
                color: navBtn.isCategory ? window.cyan : window.textPrimary
                font.family: "Bahnschrift"
                font.bold: navBtn.isCategory
                font.pixelSize: 12
                Layout.fillWidth: true
                elide: Text.ElideRight
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
                // Global STOP status: a clean result hides itself, anything else stays red.
                Rectangle {
                    visible: suiteBackend.stopAllText !== ""
                    Layout.maximumWidth: 460
                    Layout.preferredHeight: 40
                    Layout.preferredWidth: stopAllLabel.implicitWidth + 20
                    radius: 8
                    color: suiteBackend.stopAllSeverity === "error" ? "#c40018" : "transparent"
                    Text {
                        id: stopAllLabel
                        anchors.fill: parent
                        anchors.margins: 10
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        text: suiteBackend.stopAllText
                        color: suiteBackend.stopAllSeverity === "ok" ? window.green : (suiteBackend.stopAllSeverity === "busy" ? window.amber : "#ffffff")
                        font.family: "Bahnschrift"
                        font.bold: true
                        font.pixelSize: 11
                    }
                    ToolTip.visible: stopAllHover.hovered && suiteBackend.stopAllDetail !== ""
                    ToolTip.text: suiteBackend.stopAllDetail
                    HoverHandler { id: stopAllHover }
                }
                // The global STOP: one click, always visible, on every panel (F12 too).
                Button {
                    id: stopAllButton
                    objectName: "stopAllButton"
                    Layout.preferredWidth: 120
                    Layout.preferredHeight: 52
                    focusPolicy: Qt.NoFocus
                    onClicked: suiteBackend.stopAll()
                    Accessible.name: suiteBackend.uiText("STOP_ALL_TOOLTIP")
                    ToolTip.visible: hovered
                    ToolTip.text: suiteBackend.uiText("STOP_ALL_TOOLTIP")
                    background: Rectangle {
                        radius: 10
                        color: stopAllButton.down ? "#8f0012" : (stopAllButton.hovered ? "#e0001d" : "#c40018")
                        border.width: 2
                        border.color: "#ff5d6f"
                    }
                    contentItem: Column {
                        spacing: 0
                        Text { width: stopAllButton.width; horizontalAlignment: Text.AlignHCenter; text: suiteBackend.uiText("STOP_ALL_LABEL"); color: "#ffffff"; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 20 }
                        Text { width: stopAllButton.width; horizontalAlignment: Text.AlignHCenter; text: suiteBackend.uiText("STOP_ALL_CAPTION"); color: "#ffffff"; font.family: "Bahnschrift"; font.pixelSize: 10 }
                    }
                }
                Text {
                    text: suiteBackend.connectionStatus === "connected" ? "● CONNECTED" : (suiteBackend.connectionStatus === "connecting" ? "● CONNECTING" : "● DISCONNECTED")
                    color: suiteBackend.connectionStatus === "connected" ? window.green : (suiteBackend.connectionStatus === "connecting" ? window.amber : window.muted)
                    font.family: "Bahnschrift"
                    font.bold: true
                    font.pixelSize: 11
                }
                Text { text: "v" + suiteBackend.version; color: window.muted; font.family: "Bahnschrift"; font.pixelSize: 10 }
                Button {
                    id: appMenuButton
                    objectName: "appMenuButton"
                    text: "\u2261"
                    font.pixelSize: 18
                    implicitWidth: 40
                    implicitHeight: 40
                    Accessible.name: suiteBackend.uiText("MENU_FILE").replace("&", "")
                    onClicked: appMenu.popup()
                    Menu {
                        id: appMenu
                        Menu {
                            title: suiteBackend.uiText("MENU_LANGUAGE").replace("&", "")
                            Repeater {
                                model: suiteBackend.languageOptions
                                delegate: MenuItem {
                                    required property var modelData
                                    text: modelData.label
                                    checkable: true
                                    checked: modelData.current
                                    onTriggered: suiteBackend.setLanguage(modelData.code)
                                }
                            }
                        }
                        MenuItem { text: suiteBackend.uiText("BTN_EXPORT_DIAGNOSTICS"); onTriggered: diagnosticsDialog.open() }
                        MenuItem { text: suiteBackend.uiText("MENU_SHORTCUTS").replace("&", ""); onTriggered: shortcutsDialog.open() }
                        MenuItem { text: suiteBackend.uiText("MENU_ABOUT"); onTriggered: aboutDialog.open() }
                        MenuSeparator {}
                        MenuItem { text: suiteBackend.uiText("MENU_QUIT"); onTriggered: window.close() }
                    }
                }
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
            RowLayout {
                Text { text: suiteBackend.uiText("LBL_LOGIN_CODE"); color: window.muted; Layout.preferredWidth: 90; wrapMode: Text.WordWrap }
                TextField {
                    id: credentialsCodeField
                    objectName: "credentialsCodeField"
                    Layout.fillWidth: true
                    color: window.textPrimary
                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                }
            }
            CheckBox {
                id: credentialsRememberBox
                objectName: "credentialsRememberBox"
                text: suiteBackend.uiText("LBL_REMEMBER_SERVER")
                palette.windowText: window.textPrimary
            }
            Text {
                text: suiteBackend.secureStoreAvailable ? suiteBackend.uiText("HINT_REMEMBER_SECURE") : suiteBackend.uiText("HINT_REMEMBER_NO_STORE")
                color: suiteBackend.secureStoreAvailable ? window.muted : window.amber
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                Layout.preferredWidth: 330
            }
        }
        onAccepted: suiteBackend.saveServerCredentials(window.credentialsConnId, credentialsUsernameField.text, credentialsPasswordField.text, credentialsRememberBox.checked, credentialsCodeField.text)
    }

    FileDialog {
        id: diagnosticsDialog
        title: suiteBackend.uiText("TITLE_EXPORT_DIAGNOSTICS")
        fileMode: FileDialog.SaveFile
        nameFilters: ["Zip (*.zip)"]
        onAccepted: suiteBackend.exportDiagnostics(selectedFile.toString())
    }

    Dialog {
        id: shortcutsDialog
        anchors.centerIn: parent
        modal: true
        width: 420
        title: suiteBackend.uiText("TITLE_SHORTCUTS")
        standardButtons: Dialog.Close
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        contentItem: Text { text: suiteBackend.uiText("MSG_SHORTCUTS"); color: window.textPrimary; wrapMode: Text.WordWrap }
    }

    Dialog {
        id: aboutDialog
        objectName: "aboutDialog"
        anchors.centerIn: parent
        modal: true
        width: 440
        title: suiteBackend.uiText("TITLE_ABOUT")
        standardButtons: Dialog.Close
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        contentItem: ColumnLayout {
            spacing: 8
            VectorImage { Layout.alignment: Qt.AlignHCenter; Layout.preferredWidth: 88; Layout.preferredHeight: 88; source: suiteBackend.iconSource; visible: suiteBackend.iconSource !== "" }
            Text {
                Layout.alignment: Qt.AlignHCenter
                textFormat: Text.RichText
                text: "HYDRA<span style=\"color:#43db9b\">-UM</span><span style=\"color:#ee6b80\">C</span> <span style=\"color:#38d4e6\">SUITE</span>"
                color: window.textPrimary
                font.family: "Bahnschrift"
                font.bold: true
                font.pixelSize: 22
            }
            Text { text: suiteBackend.uiText("ABOUT_TAGLINE"); color: window.cyan; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true; font.pixelSize: 11 }
            Text { text: suiteBackend.uiText("ABOUT_DESCRIPTION"); color: window.muted; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true; font.pixelSize: 11 }
            GridLayout {
                columns: 2
                columnSpacing: 12
                Layout.alignment: Qt.AlignHCenter
                Text { text: suiteBackend.uiText("ABOUT_VERSION_SUITE"); color: window.muted; font.pixelSize: 11 }
                Text { text: suiteBackend.aboutInfo.version; color: window.textPrimary; font.pixelSize: 11 }
                Text { text: suiteBackend.uiText("ABOUT_VERSION_SERVER"); color: window.muted; font.pixelSize: 11 }
                Text { text: suiteBackend.aboutInfo.serverVersion; color: window.textPrimary; font.pixelSize: 11 }
                Text { text: suiteBackend.uiText("ABOUT_AUTHOR"); color: window.muted; font.pixelSize: 11 }
                Text { text: suiteBackend.aboutInfo.author; color: window.textPrimary; font.pixelSize: 11 }
                Text { text: suiteBackend.uiText("ABOUT_EMAIL"); color: window.muted; font.pixelSize: 11 }
                Text { text: suiteBackend.aboutInfo.email; color: window.textPrimary; font.pixelSize: 11 }
                Text { text: suiteBackend.uiText("ABOUT_LICENSE"); color: window.muted; font.pixelSize: 11 }
                Text { text: suiteBackend.aboutInfo.license; color: window.textPrimary; font.pixelSize: 11 }
            }
        }
    }

    FileDialog {
        id: xyTableSaveDialog
        title: suiteBackend.uiText("BTN_SAVE_CONFIG")
        fileMode: FileDialog.SaveFile
        nameFilters: ["JSON (*.json)"]
        onAccepted: suiteBackend.saveXyTableConfig(selectedFile.toString())
    }

    FileDialog {
        id: auditExportDialog
        title: suiteBackend.uiText("AUDIT_EXPORT")
        fileMode: FileDialog.SaveFile
        nameFilters: ["JSON Lines (*.jsonl)"]
        onAccepted: suiteBackend.exportAudit(selectedFile.toString())
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
                text: window.pendingConfirmLabel !== "" ? window.pendingConfirmLabel : suiteBackend.uiText("BTN_SAVE")
                Layout.fillWidth: true
                onClicked: { confirmDialog.close(); if (window.pendingConfirmAction) window.pendingConfirmAction() }
            }
        }
    }

    // A Work with points out of reach that could be loaded scaled about the base of the robot asks first.
    Connections {
        target: suiteBackend
        function onWorkScaleOffered(title, body, label) {
            window.requestConfirm(title, body, function() { suiteBackend.applyWorkScale() }, label)
        }
    }

    // What a server reported back (a refusal, a limit, a lowered target) stays here until dismissed.
    Rectangle {
        id: noticeBar
        objectName: "noticeBar"
        visible: suiteBackend.noticeText !== ""
        z: 100
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        width: Math.min(parent.width - 60, 900)
        height: noticeLabel.implicitHeight + 24
        radius: 10
        color: suiteBackend.noticeSeverity === "info" ? "#0e2f3d" : "#3a2c0a"
        border.width: 1
        border.color: suiteBackend.noticeSeverity === "info" ? window.cyan : window.amber
        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10
            Text {
                id: noticeLabel
                objectName: "noticeText"
                text: suiteBackend.noticeText
                color: suiteBackend.noticeSeverity === "info" ? "#d8f6ff" : "#ffe9b8"
                font.bold: true
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Button {
                objectName: "noticeDismiss"
                text: "×"
                implicitWidth: 30
                implicitHeight: 30
                Accessible.name: suiteBackend.uiText("BTN_CLOSE")
                onClicked: suiteBackend.dismissNotice()
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        // -- Nav sidebar - real taxonomy from qt_suite.py's own
        // rootItems/industrialItems/urtcItems/hydraumcItems/
        // hydraumcEcosystemItems, transcribed from nav_items.py's
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
                // back-to-root control nav_items.py's
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
                            active: suiteBackend.activePanel === modelData.key
                            onActivated: suiteBackend.navigatePanel(modelData.key)
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        // -- Content area - one panel at a time, the same
        // sidebar-plus-single-content-pane shape as HYDRA-UMC-STUDIO. --
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Loader {
                id: contentLoader
                anchors.fill: parent
                anchors.margins: 16
                sourceComponent: {
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
                    if (suiteBackend.activePanel === "camera_media") return cameraMediaComponent
                    if (suiteBackend.activePanel === "urtc_flasher") return flasherComponent
                    if (suiteBackend.activePanel === "hydra_flasher") return flasherComponent
                    if (suiteBackend.activePanel === "urtc_tester") return testerComponent
                    if (suiteBackend.activePanel === "hydra_tester") return testerComponent
                    if (suiteBackend.activePanel === "viewport") return viewportComponent
                    if (suiteBackend.activePanel === "robots_catalog") return robotsCatalogComponent
                    if (suiteBackend.activePanel === "safety_limits") return safetyLimitsComponent
                    if (suiteBackend.activePanel === "audit_record") return auditRecordComponent
                    if (suiteBackend.activePanel === "users") return usersComponent
                    if (suiteBackend.activePanel === "submitted_models") return submittedModelsComponent
                    if (suiteBackend.activePanel === "system_supervisor") return supervisorComponent
                    if (suiteBackend.activePanel === "ecosystem_health") return ecosystemHealthComponent
                    return null
                }
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
                CheckBox {
                    id: rememberBox
                    objectName: "rememberBox"
                    checked: true
                    text: suiteBackend.uiText("LBL_REMEMBER_SERVER")
                    palette.windowText: window.textPrimary
                }
                Button {
                    text: suiteBackend.uiText("BTN_ADD")
                    onClicked: {
                        suiteBackend.addManualServer(hostField.text, portSpin.value, userField.text, passField.text, rememberBox.checked)
                        hostField.text = ""
                    }
                }
            }
            Text {
                text: suiteBackend.secureStoreAvailable ? suiteBackend.uiText("HINT_REMEMBER_SECURE") : suiteBackend.uiText("HINT_REMEMBER_NO_STORE")
                color: suiteBackend.secureStoreAvailable ? "#556070" : window.amber
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
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
                        CheckBox {
                            checked: modelData.remembered
                            text: suiteBackend.uiText("LBL_REMEMBERED")
                            palette.windowText: window.muted
                            font.pixelSize: 10
                            onToggled: suiteBackend.setServerRemembered(modelData.connId, checked)
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
                id: accessCard
                objectName: "accessCard"
                Layout.fillWidth: true
                Layout.preferredHeight: accessColumn.implicitHeight + 24
                property bool showList: false
                ColumnLayout {
                    id: accessColumn
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Row {
                            spacing: 0
                            Button {
                                objectName: "modeLiveButton"
                                text: suiteBackend.uiText("ACCESS_MODE_LIVE")
                                checkable: true
                                checked: suiteBackend.selectedRobotMode === "live"
                                ToolTip.visible: hovered
                                ToolTip.text: suiteBackend.uiText("ACCESS_MODE_LIVE_HINT")
                                onClicked: suiteBackend.setSelectedRobotMode("live")
                            }
                            Button {
                                objectName: "modeSimButton"
                                text: suiteBackend.uiText("ACCESS_MODE_SIM")
                                checkable: true
                                checked: suiteBackend.selectedRobotMode === "sim"
                                ToolTip.visible: hovered
                                ToolTip.text: suiteBackend.uiText("ACCESS_MODE_SIM_HINT")
                                onClicked: suiteBackend.setSelectedRobotMode("sim")
                            }
                        }
                        Text {
                            visible: suiteBackend.selectedRobotMode === "sim"
                            text: suiteBackend.uiText("ACCESS_SIM_NOTICE")
                            color: window.amber
                            font.bold: true
                            font.pixelSize: 11
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                        }
                        Rectangle {
                            height: 32
                            width: badgeText.implicitWidth + 20
                            radius: 8
                            color: suiteBackend.selectedRobotAccess.standing === "mine" ? "#123a1c"
                                : (suiteBackend.selectedRobotAccess.standing === "free" ? window.panelAlt
                                : (suiteBackend.selectedRobotAccess.standing === "other-controller" ? "#3a2c0a" : "#3a1018"))
                            Text {
                                id: badgeText
                                objectName: "accessBadge"
                                anchors.centerIn: parent
                                text: suiteBackend.selectedRobotAccess.text
                                color: window.textPrimary
                                font.bold: true
                                font.pixelSize: 11
                            }
                        }
                        Button {
                            objectName: "reserveButton"
                            visible: suiteBackend.selectedRobotAccess.canReserve
                            enabled: !suiteBackend.accessBusy
                            text: suiteBackend.uiText("ACCESS_RESERVE")
                            onClicked: suiteBackend.claimSelectedRobot()
                        }
                        Button {
                            objectName: "releaseButton"
                            visible: suiteBackend.selectedRobotAccess.canRelease
                            enabled: !suiteBackend.accessBusy
                            text: suiteBackend.uiText("ACCESS_RELEASE")
                            onClicked: suiteBackend.releaseSelectedRobot()
                        }
                        Button {
                            objectName: "takeOverButton"
                            visible: suiteBackend.selectedRobotAccess.canTakeOver
                            enabled: !suiteBackend.accessBusy
                            text: suiteBackend.uiText("ACCESS_TAKE_OVER")
                            onClicked: window.requestConfirm(
                                suiteBackend.uiText("ACCESS_TAKE_OVER"),
                                suiteBackend.uiText("ACCESS_CONFIRM_TAKE_OVER"),
                                function() { suiteBackend.takeOverSelectedRobot() },
                                suiteBackend.uiText("ACCESS_TAKE_OVER"))
                        }
                        Button {
                            objectName: "jogArmButton"
                            visible: suiteBackend.jogArmRequired
                            enabled: !suiteBackend.accessBusy && suiteBackend.selectedRobotArm.canToggle
                            text: suiteBackend.selectedRobotArm.armed
                                ? suiteBackend.uiText("ACCESS_DISARM") + " (" + suiteBackend.selectedRobotArm.seconds + " s)"
                                : suiteBackend.uiText("ACCESS_ARM")
                            ToolTip.visible: hovered
                            ToolTip.text: suiteBackend.uiText("ACCESS_ARM_HINT")
                            onClicked: suiteBackend.toggleJogArm()
                        }
                        Rectangle {
                            visible: suiteBackend.selectedRobotSafeMode.disabled === true
                            height: 32
                            width: safeModeText.implicitWidth + 20
                            radius: 8
                            color: "#3a1018"
                            Text {
                                id: safeModeText
                                objectName: "safeModeBadge"
                                anchors.centerIn: parent
                                text: suiteBackend.selectedRobotSafeMode.text
                                color: window.textPrimary
                                font.bold: true
                                font.pixelSize: 11
                            }
                        }
                        Button {
                            objectName: "safeModeDisableButton"
                            visible: suiteBackend.selectedRobotSafeMode.canDisable === true
                            enabled: !suiteBackend.accessBusy
                            text: suiteBackend.uiText("ACCESS_DISABLE")
                            ToolTip.visible: hovered
                            ToolTip.text: suiteBackend.uiText("ACCESS_DISABLE_HINT")
                            onClicked: suiteBackend.disableSelectedRobot()
                        }
                        Button {
                            objectName: "safeModeEnableButton"
                            visible: suiteBackend.selectedRobotSafeMode.canEnable === true
                            enabled: !suiteBackend.accessBusy
                            text: suiteBackend.uiText("ACCESS_ENABLE")
                            ToolTip.visible: hovered
                            ToolTip.text: suiteBackend.uiText("ACCESS_ENABLE_HINT")
                            onClicked: window.requestConfirm(
                                suiteBackend.uiText("ACCESS_ENABLE"),
                                suiteBackend.uiText("ACCESS_CONFIRM_ENABLE"),
                                function() { suiteBackend.enableSelectedRobot() },
                                suiteBackend.uiText("ACCESS_ENABLE"))
                        }
                        Button {
                            objectName: "claimsListButton"
                            flat: true
                            text: suiteBackend.uiText("ACCESS_LIST_TOGGLE") + " (" + suiteBackend.claimsRows.length + ")"
                            onClicked: accessCard.showList = !accessCard.showList
                        }
                    }
                    ColumnLayout {
                        visible: accessCard.showList
                        Layout.fillWidth: true
                        spacing: 3
                        Text { visible: suiteBackend.claimsRows.length === 0; text: suiteBackend.uiText("ACCESS_LIST_EMPTY"); color: "#556070"; font.pixelSize: 11 }
                        Repeater {
                            model: suiteBackend.claimsRows
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 10
                                Text { text: modelData.robot; color: modelData.mine ? window.green : window.textPrimary; font.bold: true; font.pixelSize: 11; Layout.preferredWidth: 150 }
                                Text { text: modelData.owner; color: window.muted; font.pixelSize: 11; Layout.preferredWidth: 130 }
                                Text { text: modelData.controller; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: modelData.left; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                            }
                        }
                        CheckBox {
                            text: suiteBackend.uiText("ACCESS_DEFAULT_SIM")
                            checked: suiteBackend.defaultRobotModeSim
                            palette.windowText: window.muted
                            onToggled: suiteBackend.setDefaultRobotModeSim(checked)
                        }
                        RowLayout {
                            spacing: 8
                            Text { text: suiteBackend.uiText("ACCESS_CONDITIONAL_LABEL"); color: window.muted; font.pixelSize: 11 }
                            ComboBox {
                                id: conditionalCombo
                                objectName: "conditionalModeCombo"
                                Layout.preferredWidth: 340
                                model: suiteBackend.conditionalModeOptions
                                textRole: "label"
                                valueRole: "value"
                                Component.onCompleted: currentIndex = indexOfValue(suiteBackend.conditionalMode)
                                onActivated: suiteBackend.setConditionalMode(currentValue)
                                ToolTip.visible: hovered
                                ToolTip.text: suiteBackend.uiText("ACCESS_CONDITIONAL_HINT")
                            }
                        }
                    }
                }
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
                                from: modelData.min; to: modelData.max
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
                Layout.preferredHeight: 150
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Text { text: suiteBackend.uiText("GROUP_PLAYBACK"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                    RowLayout {
                        spacing: 8
                        Button { objectName: "playButton"; text: suiteBackend.uiText("BTN_PLAYBACK_PLAY"); enabled: suiteBackend.selectedRobotTransport.canPlay; onClicked: suiteBackend.playSelectedRobot() }
                        Button { objectName: "pauseButton"; text: suiteBackend.selectedRobotTransport.paused ? suiteBackend.uiText("BTN_PLAYBACK_CONTINUE") : suiteBackend.uiText("BTN_PLAYBACK_PAUSE"); enabled: suiteBackend.selectedRobotTransport.canPause; onClicked: suiteBackend.pauseSelectedRobot() }
                        Button { objectName: "stopButton"; text: suiteBackend.uiText("BTN_PLAYBACK_STOP"); enabled: suiteBackend.selectedRobotTransport.canStop; onClicked: suiteBackend.stopSelectedRobot() }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: suiteBackend.uiText("LBL_SPEED"); color: window.muted; Layout.preferredWidth: 90 }
                        Slider { Layout.fillWidth: true; from: 10; to: 500; value: suiteBackend.selectedRobotSpeed; enabled: suiteBackend.canControlRobot; onMoved: suiteBackend.setRobotSpeed(Math.round(value)) }
                        Text { text: suiteBackend.selectedRobotSpeed + "%"; color: window.textPrimary; Layout.preferredWidth: 45 }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: suiteBackend.uiText("LBL_ACCELERATION"); color: window.muted; Layout.preferredWidth: 90 }
                        Slider { Layout.fillWidth: true; from: 10; to: 500; value: suiteBackend.selectedRobotAcceleration; enabled: suiteBackend.canControlRobot; onMoved: suiteBackend.setRobotAcceleration(Math.round(value)) }
                        Text { text: suiteBackend.selectedRobotAcceleration + "%"; color: window.textPrimary; Layout.preferredWidth: 45 }
                    }
                }
            }
            Card {
                Layout.fillWidth: true
                Layout.preferredHeight: ioColumn.implicitHeight + 28
                ColumnLayout {
                    id: ioColumn
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Text { text: suiteBackend.uiText("GROUP_TOOL_ACCESSORIES"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                    RowLayout {
                        spacing: 8
                        Text { text: suiteBackend.uiText("LBL_URTC_TOOL"); color: window.muted; Layout.preferredWidth: 90 }
                        ComboBox {
                            id: toolCombo
                            objectName: "toolCombo"
                            Layout.preferredWidth: 320
                            enabled: suiteBackend.canControlRobot
                            model: suiteBackend.toolOptions
                            currentIndex: model.indexOf(suiteBackend.selectedRobotTool)
                            Connections {
                                target: suiteBackend
                                function onChanged() { toolCombo.currentIndex = toolCombo.model.indexOf(suiteBackend.selectedRobotTool) }
                            }
                            // The tool decides what the robot does with the following moves: it asks first, and
                            // declining puts the selector back on the tool the robot really has.
                            onActivated: {
                                var chosen = model[currentIndex]
                                currentIndex = model.indexOf(suiteBackend.selectedRobotTool)
                                if (chosen !== suiteBackend.selectedRobotTool) {
                                    window.requestConfirm(
                                        suiteBackend.uiText("TITLE_CONFIRM_TOOL"),
                                        suiteBackend.uiText("MSG_CONFIRM_TOOL").replace("{tool}", chosen),
                                        function() { suiteBackend.setSelectedRobotTool(chosen) },
                                        suiteBackend.uiText("TITLE_CONFIRM_TOOL"))
                                }
                            }
                        }
                    }
                    RowLayout {
                        spacing: 8
                        Repeater {
                            model: 2
                            delegate: Button {
                                required property int index
                                text: suiteBackend.uiText(index === 0 ? "LBL_VALVE_1" : "LBL_VALVE_2")
                                checkable: true
                                checked: suiteBackend.selectedRobotValves[index] === true
                                enabled: suiteBackend.canControlRobot
                                onClicked: suiteBackend.setSelectedValve(index, checked)
                            }
                        }
                        Repeater {
                            model: 2
                            delegate: Button {
                                required property int index
                                text: suiteBackend.uiText(index === 0 ? "LBL_PUMP_1" : "LBL_PUMP_2")
                                checkable: true
                                checked: suiteBackend.selectedRobotPumps[index] === true
                                enabled: suiteBackend.canControlRobot
                                onClicked: suiteBackend.setSelectedPump(index, checked)
                            }
                        }
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
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Button {
                    objectName: "exportWorkButton"
                    text: suiteBackend.uiText("BTN_EXPORT_WORK")
                    enabled: suiteBackend.trajectoryPoints.length > 0
                    onClicked: { workNameField.text = "trajectory_1"; exportWorkDialog.open() }
                }
                Button {
                    objectName: "importWorkButton"
                    text: suiteBackend.uiText("BTN_IMPORT_WORK")
                    enabled: suiteBackend.canControlRobot
                    onClicked: { suiteBackend.refreshWorkFiles(); importWorkDialog.open() }
                }
            }
            Dialog {
                id: exportWorkDialog
                anchors.centerIn: Overlay.overlay
                modal: true
                width: 380
                title: suiteBackend.uiText("DLG_EXPORT_WORK_TITLE")
                standardButtons: Dialog.Ok | Dialog.Cancel
                background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
                contentItem: ColumnLayout {
                    spacing: 8
                    Text { text: suiteBackend.uiText("DLG_EXPORT_WORK_LABEL"); color: window.muted }
                    TextField {
                        id: workNameField
                        objectName: "workNameField"
                        Layout.fillWidth: true
                        color: window.textPrimary
                        background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                    }
                }
                onAccepted: suiteBackend.exportWork(workNameField.text)
            }
            Dialog {
                id: importWorkDialog
                anchors.centerIn: Overlay.overlay
                modal: true
                width: 380
                height: 360
                title: suiteBackend.uiText("DLG_IMPORT_WORK_TITLE")
                standardButtons: Dialog.Cancel
                background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
                contentItem: ColumnLayout {
                    spacing: 8
                    Text { text: suiteBackend.uiText("DLG_IMPORT_WORK_LABEL"); color: window.muted }
                    ListView {
                        objectName: "workFilesList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 3
                        model: suiteBackend.workFiles
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            height: 30
                            radius: 6
                            color: window.panelAlt
                            Text { anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 8; text: modelData; color: window.textPrimary; font.pixelSize: 11 }
                            MouseArea { anchors.fill: parent; onClicked: { importWorkDialog.close(); suiteBackend.importWork(modelData) } }
                        }
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
                // the former admin_clients panel's _rebuild(): shown
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
                Layout.preferredHeight: 120
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
            Text { text: suiteBackend.uiText("CONNECTIONS_TITLE"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 14 }
            Text { text: suiteBackend.uiText("CONNECTIONS_DESC"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { visible: suiteBackend.connectionHistoryStatus !== ""; text: suiteBackend.connectionHistoryStatus; color: "#ee6b80"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { text: suiteBackend.uiText("CONNECTIONS_CLIENTS_TITLE"); color: window.muted; font.pixelSize: 9; font.bold: true }
            Text { visible: suiteBackend.connectionHistoryStatus === "" && suiteBackend.connectionClientRows.length === 0; text: suiteBackend.uiText("CONNECTIONS_CLIENTS_NONE"); color: "#556070"; font.pixelSize: 11 }
            ListView {
                objectName: "connectionClientList"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 110
                clip: true
                model: suiteBackend.connectionClientRows
                spacing: 4
                delegate: Card {
                    required property var modelData
                    width: ListView.view.width
                    height: 42
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10
                        ColumnLayout {
                            spacing: 2
                            Layout.fillWidth: true
                            Text { text: modelData.who; color: window.textPrimary; font.bold: true; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text { text: modelData.detail; color: "#556070"; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                        Text { visible: modelData.twoFactor; text: "2FA"; color: window.green; font.bold: true; font.pixelSize: 9 }
                        Text { text: modelData.sessions; color: modelData.active ? window.green : window.muted; font.pixelSize: 9 }
                        Text { text: modelData.logins; color: window.muted; font.pixelSize: 9 }
                        Text { text: modelData.lastSeen; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 9 }
                    }
                }
            }
            Text { text: suiteBackend.uiText("CONNECTIONS_EVENTS_TITLE"); color: window.muted; font.pixelSize: 9; font.bold: true }
            Text { visible: suiteBackend.connectionHistoryStatus === "" && suiteBackend.connectionEventRows.length === 0; text: suiteBackend.uiText("CONNECTIONS_EVENTS_NONE"); color: "#556070"; font.pixelSize: 11 }
            ListView {
                objectName: "connectionEventList"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 110
                clip: true
                model: suiteBackend.connectionEventRows
                spacing: 2
                delegate: RowLayout {
                    required property var modelData
                    width: ListView.view.width
                    spacing: 8
                    Text { text: modelData.action; color: modelData.failure ? "#ee6b80" : window.textPrimary; font.bold: modelData.failure; font.pixelSize: 10 }
                    Text { text: modelData.detail; color: "#556070"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                    Text { text: modelData.ago; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 9 }
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
                // the copy button of the log: an icon of two sheets that puts every line on the clipboard (through a hidden text box, which can copy)
                Rectangle {
                    id: copyIconButton
                    property bool copied: false
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 32
                    radius: 8
                    color: copyIconMouse.containsMouse ? "#1b3c52" : "#102a3b"
                    border.width: 1
                    border.color: copyIconButton.copied ? "#5df0c4" : "#264966"
                    Item {
                        anchors.centerIn: parent
                        width: 18; height: 18
                        Rectangle { x: 6; y: 0; width: 11; height: 12; radius: 2; color: "transparent"; border.width: 1.6; border.color: copyIconButton.copied ? "#5df0c4" : "#9fd8e3" }
                        Rectangle { x: 1; y: 5; width: 11; height: 12; radius: 2; color: copyIconMouse.containsMouse ? "#1b3c52" : "#102a3b"; border.width: 1.6; border.color: copyIconButton.copied ? "#5df0c4" : "#9fd8e3" }
                    }
                    TextEdit { id: copyHelper; visible: false }
                    Timer { id: copiedTimer; interval: 1400; onTriggered: copyIconButton.copied = false }
                    MouseArea {
                        id: copyIconMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            copyHelper.text = suiteBackend.adminLogsLines.join("\n")
                            copyHelper.selectAll(); copyHelper.copy(); copyHelper.deselect()
                            copyIconButton.copied = true; copiedTimer.restart()
                        }
                    }
                }
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
        Flickable {
            width: contentLoader.width
            height: contentLoader.height
            contentWidth: width
            contentHeight: adminServerColumn.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
        ColumnLayout {
            id: adminServerColumn
            width: parent.width - 12
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
            Card {
                visible: suiteBackend.securityView.available === true
                objectName: "securityCard"
                Layout.fillWidth: true
                Layout.preferredHeight: securityColumn.implicitHeight + 24
                ColumnLayout {
                    id: securityColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8
                    Text { text: suiteBackend.uiText("HEADING_ADMIN_SECURITY"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                    Text { visible: suiteBackend.securityWarning !== ""; text: suiteBackend.securityWarning; color: window.amber; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                    Text { visible: suiteBackend.securityError !== ""; text: suiteBackend.securityError; color: "#ee6b80"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10; font.bold: true }
                    Text { visible: suiteBackend.securityMessage !== ""; text: suiteBackend.securityMessage; color: window.green; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10; font.bold: true }
                    Text { text: suiteBackend.uiText("LBL_SECURITY_AI"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                    ComboBox {
                        objectName: "securityAiCombo"
                        Layout.fillWidth: true
                        model: suiteBackend.securityAiOptions
                        textRole: "label"
                        valueRole: "value"
                        enabled: !suiteBackend.securityView.aiLocked
                        currentIndex: Math.max(0, indexOfValue(suiteBackend.securityView.aiValue))
                        onActivated: suiteBackend.setAiAccess(currentValue)
                    }
                    Text { text: suiteBackend.securityView.aiSource; color: "#556070"; font.pixelSize: 9 }
                    CheckBox {
                        objectName: "securityInfoBox"
                        text: suiteBackend.uiText("LBL_SECURITY_INFO")
                        palette.windowText: window.textPrimary
                        enabled: !suiteBackend.securityView.infoLocked
                        checked: suiteBackend.securityView.infoValue === true
                        onClicked: {
                            var wanted = checked
                            checked = Qt.binding(function() { return suiteBackend.securityView.infoValue === true })
                            if (suiteBackend.infoAuthNeedsConfirmation(wanted))
                                window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_INFO_OFF"), suiteBackend.uiText("MSG_SECURITY_INFO_OFF_CONFIRM"), function() { suiteBackend.setInfoAuth(false) })
                            else
                                suiteBackend.setInfoAuth(wanted)
                        }
                    }
                    Text { text: suiteBackend.securityView.infoSource; color: "#556070"; font.pixelSize: 9 }
                    CheckBox {
                        id: tlsBox
                        objectName: "securityTlsBox"
                        text: suiteBackend.uiText("LBL_SECURITY_TLS")
                        palette.windowText: window.textPrimary
                        enabled: !suiteBackend.securityView.tlsLocked
                        checked: suiteBackend.securityView.tlsEnabled === true
                    }
                    TextField {
                        id: tlsCertField
                        objectName: "securityTlsCert"
                        Layout.fillWidth: true
                        enabled: !suiteBackend.securityView.tlsLocked
                        placeholderText: suiteBackend.uiText("PH_SECURITY_TLS_CERT")
                        text: suiteBackend.securityView.tlsCert
                        color: window.textPrimary
                        background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                    }
                    TextField {
                        id: tlsKeyField
                        objectName: "securityTlsKey"
                        Layout.fillWidth: true
                        enabled: !suiteBackend.securityView.tlsLocked
                        placeholderText: suiteBackend.uiText("PH_SECURITY_TLS_KEY")
                        text: suiteBackend.securityView.tlsKey
                        color: window.textPrimary
                        background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                    }
                    RowLayout {
                        spacing: 8
                        Button { objectName: "securityTlsSave"; text: suiteBackend.uiText("BTN_SAVE"); enabled: !suiteBackend.securityView.tlsLocked; onClicked: suiteBackend.saveTlsOptions(tlsBox.checked, tlsCertField.text, tlsKeyField.text) }
                        Text { text: suiteBackend.securityView.tlsSource; color: "#556070"; font.pixelSize: 9 }
                    }
                    Text { text: suiteBackend.uiText("LBL_SECURITY_TLS_FINGERPRINT") + ": " + suiteBackend.securityView.tlsFingerprint; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 9; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                    Text { text: suiteBackend.securityView.tlsStatus; color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    ColumnLayout {
                        visible: suiteBackend.securityView.bleAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_BLE"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        ComboBox {
                            id: bleModeCombo
                            objectName: "securityBleCombo"
                            Layout.fillWidth: true
                            model: suiteBackend.securityBleModes
                            textRole: "label"
                            valueRole: "value"
                            enabled: !suiteBackend.securityView.bleModeLocked
                            currentIndex: Math.max(0, indexOfValue(suiteBackend.securityView.bleMode))
                            onActivated: {
                                var mode = currentValue
                                currentIndex = Qt.binding(function() { return Math.max(0, indexOfValue(suiteBackend.securityView.bleMode)) })
                                var encrypted = suiteBackend.securityView.bleEncryption === true
                                if (suiteBackend.bleNeedsConfirmation(mode, encrypted))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_BLE_UNENCRYPTED"), suiteBackend.uiText("MSG_SECURITY_BLE_UNENCRYPTED_CONFIRM"), function() { suiteBackend.setBleOptions(mode, encrypted) })
                                else
                                    suiteBackend.setBleOptions(mode, encrypted)
                            }
                        }
                        Text { text: suiteBackend.securityView.bleModeSource; color: "#556070"; font.pixelSize: 9 }
                        CheckBox {
                            objectName: "securityBleEncryptionBox"
                            text: suiteBackend.uiText("LBL_SECURITY_BLE_ENCRYPTION")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.bleEncryptionLocked
                            checked: suiteBackend.securityView.bleEncryption === true
                            onClicked: {
                                var wanted = checked
                                checked = Qt.binding(function() { return suiteBackend.securityView.bleEncryption === true })
                                var mode = suiteBackend.securityView.bleMode
                                if (suiteBackend.bleNeedsConfirmation(mode, wanted))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_BLE_UNENCRYPTED"), suiteBackend.uiText("MSG_SECURITY_BLE_UNENCRYPTED_CONFIRM"), function() { suiteBackend.setBleOptions(mode, wanted) })
                                else
                                    suiteBackend.setBleOptions(mode, wanted)
                            }
                        }
                        Text { text: suiteBackend.securityView.bleEncryptionSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.securityView.bleRunning; color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.mqttAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_MQTT"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        ComboBox {
                            id: mqttModeCombo
                            objectName: "securityMqttCombo"
                            Layout.fillWidth: true
                            model: suiteBackend.securityMqttModes
                            textRole: "label"
                            valueRole: "value"
                            enabled: !suiteBackend.securityView.mqttModeLocked
                            currentIndex: Math.max(0, indexOfValue(suiteBackend.securityView.mqttMode))
                        }
                        Text { text: suiteBackend.securityView.mqttModeSource; color: "#556070"; font.pixelSize: 9 }
                        TextField {
                            id: mqttUrlField
                            objectName: "securityMqttUrl"
                            Layout.fillWidth: true
                            placeholderText: suiteBackend.uiText("PH_SECURITY_MQTT_URL")
                            text: suiteBackend.securityView.mqttUrl
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        TextField {
                            id: mqttPrefixField
                            objectName: "securityMqttPrefix"
                            Layout.fillWidth: true
                            placeholderText: suiteBackend.uiText("PH_SECURITY_MQTT_PREFIX")
                            text: suiteBackend.securityView.mqttPrefix
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        TextField {
                            id: mqttUserField
                            objectName: "securityMqttUser"
                            Layout.fillWidth: true
                            placeholderText: suiteBackend.uiText("PH_SECURITY_MQTT_USER")
                            text: suiteBackend.securityView.mqttUser
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        TextField {
                            id: mqttCommandUserField
                            objectName: "securityMqttCommandUser"
                            Layout.fillWidth: true
                            placeholderText: suiteBackend.uiText("PH_SECURITY_MQTT_COMMAND_USER")
                            text: suiteBackend.securityView.mqttCommandUser
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_MQTT_PASSWORDS"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityMqttSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            onClicked: {
                                var mode = mqttModeCombo.currentValue
                                var url = mqttUrlField.text, prefix = mqttPrefixField.text, user = mqttUserField.text, commandUser = mqttCommandUserField.text
                                if (suiteBackend.mqttNeedsConfirmation(mode))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_MQTT_COMMANDS"), suiteBackend.uiText("MSG_SECURITY_MQTT_COMMANDS_CONFIRM"), function() { suiteBackend.saveMqttOptions(mode, url, prefix, user, commandUser) })
                                else
                                    suiteBackend.saveMqttOptions(mode, url, prefix, user, commandUser)
                            }
                        }
                        Text { text: suiteBackend.securityView.mqttRunning; color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.voiceAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_VOICE"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        CheckBox {
                            id: voiceHeardBox
                            objectName: "securityVoiceHeardBox"
                            text: suiteBackend.uiText("LBL_SECURITY_VOICE_HEARD")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.voiceHeardLocked
                            checked: suiteBackend.securityView.voiceHeard === true
                        }
                        Text { text: suiteBackend.securityView.voiceHeardSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_VOICE_CONFIDENCE"); color: window.textPrimary; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        TextField {
                            id: voiceConfidenceField
                            objectName: "securityVoiceConfidence"
                            Layout.fillWidth: true
                            enabled: !suiteBackend.securityView.voiceConfidenceLocked
                            text: suiteBackend.securityView.voiceConfidence
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        Text { text: suiteBackend.securityView.voiceConfidenceSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_VOICE_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityVoiceSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !(suiteBackend.securityView.voiceHeardLocked && suiteBackend.securityView.voiceConfidenceLocked)
                            onClicked: {
                                var heard = voiceHeardBox.checked, confidence = voiceConfidenceField.text
                                if (suiteBackend.voiceNeedsConfirmation(heard, confidence))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_VOICE"), suiteBackend.uiText("MSG_SECURITY_VOICE_CONFIRM"), function() { suiteBackend.saveVoiceOptions(heard, confidence) })
                                else
                                    suiteBackend.saveVoiceOptions(heard, confidence)
                            }
                        }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.robotsAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_ROBOTS"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        CheckBox {
                            id: robotsAllowEnableBox
                            objectName: "securityRobotsAllowEnableBox"
                            text: suiteBackend.uiText("LBL_SECURITY_ROBOTS_ENABLE")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.robotsAllowEnableLocked
                            checked: suiteBackend.securityView.robotsAllowEnable === true
                        }
                        Text { text: suiteBackend.securityView.robotsAllowEnableSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_ROBOTS_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityRobotsSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !suiteBackend.securityView.robotsAllowEnableLocked
                            onClicked: {
                                var allow = robotsAllowEnableBox.checked
                                if (suiteBackend.robotsNeedsConfirmation(allow))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_ROBOTS"), suiteBackend.uiText("MSG_SECURITY_ROBOTS_CONFIRM"), function() { suiteBackend.saveRobotsOptions(allow) })
                                else
                                    suiteBackend.saveRobotsOptions(allow)
                            }
                        }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.healthAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_HEALTH"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        CheckBox {
                            id: healthOpenBox
                            objectName: "securityHealthOpenBox"
                            text: suiteBackend.uiText("LBL_SECURITY_HEALTH_OPEN")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.healthOpenLocked
                            checked: suiteBackend.securityView.healthOpen === true
                        }
                        Text { text: suiteBackend.securityView.healthOpenSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_HEALTH_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityHealthSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !suiteBackend.securityView.healthOpenLocked
                            onClicked: {
                                var open = healthOpenBox.checked
                                if (suiteBackend.healthNeedsConfirmation(open))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_HEALTH"), suiteBackend.uiText("MSG_SECURITY_HEALTH_CONFIRM"), function() { suiteBackend.saveHealthOptions(open) })
                                else
                                    suiteBackend.saveHealthOptions(open)
                            }
                        }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.safetyAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_STOP"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        CheckBox {
                            id: safetyPublishBox
                            objectName: "securitySafetyPublishBox"
                            text: suiteBackend.uiText("LBL_SECURITY_STOP_PUBLISH")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.safetyPublishStopLocked
                            checked: suiteBackend.securityView.safetyPublishStop === true
                        }
                        Text { text: suiteBackend.securityView.safetyPublishStopSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_STOP_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securitySafetySave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !suiteBackend.securityView.safetyPublishStopLocked
                            onClicked: suiteBackend.saveSafetyOptions(safetyPublishBox.checked)
                        }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.ecosystemHealthAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_ECOHEALTH"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        CheckBox {
                            id: ecosystemHealthBox
                            objectName: "securityEcosystemHealthBox"
                            text: suiteBackend.uiText("LBL_SECURITY_ECOHEALTH_ENABLED")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.ecosystemHealthEnabledLocked
                            checked: suiteBackend.securityView.ecosystemHealthEnabled === true
                        }
                        Text { text: suiteBackend.securityView.ecosystemHealthEnabledSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_ECOHEALTH_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityEcosystemHealthSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !suiteBackend.securityView.ecosystemHealthEnabledLocked
                            onClicked: suiteBackend.saveEcosystemHealthOptions(ecosystemHealthBox.checked)
                        }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.rulAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_RUL"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        CheckBox {
                            id: rulBox
                            objectName: "securityRulBox"
                            text: suiteBackend.uiText("LBL_SECURITY_RUL_ENABLED")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.rulEnabledLocked
                            checked: suiteBackend.securityView.rulEnabled === true
                        }
                        Text { text: suiteBackend.securityView.rulEnabledSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_RUL_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityRulSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !suiteBackend.securityView.rulEnabledLocked
                            onClicked: suiteBackend.saveRulOptions(rulBox.checked)
                        }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.connectionsAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_CONNECTIONS"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        CheckBox {
                            id: connectionsRecordBox
                            objectName: "securityConnectionsRecordBox"
                            text: suiteBackend.uiText("LBL_SECURITY_CONNECTIONS_RECORD")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.connectionsRecordLocked
                            checked: suiteBackend.securityView.connectionsRecord === true
                        }
                        Text { text: suiteBackend.securityView.connectionsRecordSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_CONNECTIONS_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityConnectionsSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !suiteBackend.securityView.connectionsRecordLocked
                            onClicked: {
                                var record = connectionsRecordBox.checked
                                if (suiteBackend.connectionsNeedsConfirmation(record))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_CONNECTIONS"), suiteBackend.uiText("MSG_SECURITY_CONNECTIONS_CONFIRM"), function() { suiteBackend.saveConnectionsOptions(record) })
                                else
                                    suiteBackend.saveConnectionsOptions(record)
                            }
                        }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.exposureAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_EXPOSURE"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        CheckBox {
                            id: exposureCameraBox
                            objectName: "securityExposureCameraBox"
                            text: suiteBackend.uiText("LBL_SECURITY_EXPOSURE_CAMERA")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.exposureCameraOpenLocked
                            checked: suiteBackend.securityView.exposureCameraOpen === true
                        }
                        Text { text: suiteBackend.securityView.exposureCameraOpenSource; color: "#556070"; font.pixelSize: 9 }
                        CheckBox {
                            id: exposureWsBox
                            objectName: "securityExposureWsBox"
                            text: suiteBackend.uiText("LBL_SECURITY_EXPOSURE_WS")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.exposureWsQueryTokenLocked
                            checked: suiteBackend.securityView.exposureWsQueryToken === true
                        }
                        Text { text: suiteBackend.securityView.exposureWsQueryTokenSource; color: "#556070"; font.pixelSize: 9 }
                        CheckBox {
                            id: exposureLogBox
                            objectName: "securityExposureLogBox"
                            text: suiteBackend.uiText("LBL_SECURITY_EXPOSURE_LOG")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.exposureLogRedactionLocked
                            checked: suiteBackend.securityView.exposureLogRedaction === true
                        }
                        Text { text: suiteBackend.securityView.exposureLogRedactionSource; color: "#556070"; font.pixelSize: 9 }
                        CheckBox {
                            id: exposureVoiceBox
                            objectName: "securityExposureVoiceBox"
                            text: suiteBackend.uiText("LBL_SECURITY_EXPOSURE_VOICE")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.exposureVoiceSignatureLocked
                            checked: suiteBackend.securityView.exposureVoiceSignature === true
                        }
                        Text { text: suiteBackend.securityView.exposureVoiceSignatureSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_EXPOSURE_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityExposureSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !(suiteBackend.securityView.exposureCameraOpenLocked && suiteBackend.securityView.exposureWsQueryTokenLocked && suiteBackend.securityView.exposureLogRedactionLocked && suiteBackend.securityView.exposureVoiceSignatureLocked)
                            onClicked: {
                                var camera = exposureCameraBox.checked, ws = exposureWsBox.checked, log = exposureLogBox.checked, voice = exposureVoiceBox.checked
                                if (suiteBackend.exposureNeedsConfirmation(camera, ws, log, voice))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_EXPOSURE"), suiteBackend.uiText("MSG_SECURITY_EXPOSURE_CONFIRM"), function() { suiteBackend.saveExposureOptions(camera, ws, log, voice) })
                                else
                                    suiteBackend.saveExposureOptions(camera, ws, log, voice)
                            }
                        }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.installAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_INSTALL"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        CheckBox {
                            id: installCameraBox
                            objectName: "securityInstallCameraBox"
                            text: suiteBackend.uiText("LBL_SECURITY_INSTALL_CAMERA")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.installCameraCredentialsViaEnvLocked
                            checked: suiteBackend.securityView.installCameraCredentialsViaEnv === true
                        }
                        Text { text: suiteBackend.securityView.installCameraCredentialsViaEnvSource; color: "#556070"; font.pixelSize: 9 }
                        CheckBox {
                            id: installTlsBox
                            objectName: "securityInstallTlsBox"
                            text: suiteBackend.uiText("LBL_SECURITY_INSTALL_TLS")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.installNewInstallTlsLocked
                            checked: suiteBackend.securityView.installNewInstallTls === true
                        }
                        Text { text: suiteBackend.securityView.installNewInstallTlsSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_INSTALL_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityInstallSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !(suiteBackend.securityView.installCameraCredentialsViaEnvLocked && suiteBackend.securityView.installNewInstallTlsLocked)
                            onClicked: {
                                var camera = installCameraBox.checked, tls = installTlsBox.checked
                                if (suiteBackend.installNeedsConfirmation(camera, tls))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_INSTALL"), suiteBackend.uiText("MSG_SECURITY_INSTALL_CONFIRM"), function() { suiteBackend.saveInstallOptions(camera, tls) })
                                else
                                    suiteBackend.saveInstallOptions(camera, tls)
                            }
                        }
                    }
                    ColumnLayout {
                        visible: suiteBackend.securityView.mavlinkAvailable === true
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("LBL_SECURITY_MAVLINK"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_MAVLINK_KEY"); color: window.textPrimary; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        TextField {
                            id: mavlinkKeyField
                            objectName: "securityMavlinkKey"
                            Layout.fillWidth: true
                            enabled: !suiteBackend.securityView.mavlinkKeyLocked
                            placeholderText: suiteBackend.uiText("PH_SECURITY_MAVLINK_KEY")
                            text: suiteBackend.securityView.mavlinkKey
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        Text { text: suiteBackend.securityView.mavlinkKeySource; color: "#556070"; font.pixelSize: 9 }
                        CheckBox {
                            id: mavlinkUnsignedBox
                            objectName: "securityMavlinkUnsignedBox"
                            text: suiteBackend.uiText("LBL_SECURITY_MAVLINK_UNSIGNED")
                            palette.windowText: window.textPrimary
                            enabled: !suiteBackend.securityView.mavlinkUnsignedLocked
                            checked: suiteBackend.securityView.mavlinkUnsigned === true
                        }
                        Text { text: suiteBackend.securityView.mavlinkUnsignedSource; color: "#556070"; font.pixelSize: 9 }
                        Text { text: suiteBackend.uiText("LBL_SECURITY_MAVLINK_HELP"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "securityMavlinkSave"
                            text: suiteBackend.uiText("BTN_SAVE")
                            enabled: !(suiteBackend.securityView.mavlinkKeyLocked && suiteBackend.securityView.mavlinkUnsignedLocked)
                            onClicked: {
                                var key = mavlinkKeyField.text, unsigned = mavlinkUnsignedBox.checked
                                if (suiteBackend.mavlinkNeedsConfirmation(key, unsigned))
                                    window.requestConfirm(suiteBackend.uiText("TITLE_SECURITY_MAVLINK"), suiteBackend.uiText("MSG_SECURITY_MAVLINK_CONFIRM"), function() { suiteBackend.saveMavlinkOptions(key, unsigned) })
                                else
                                    suiteBackend.saveMavlinkOptions(key, unsigned)
                            }
                        }
                        Text { text: suiteBackend.securityView.mavlinkStatus; color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                }
            }
            Card {
                visible: suiteBackend.totpStep !== "none"
                objectName: "totpCard"
                Layout.fillWidth: true
                Layout.preferredHeight: totpColumn.implicitHeight + 24
                ColumnLayout {
                    id: totpColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 8
                    Text { text: suiteBackend.uiText("HEADING_TOTP"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                    Text { text: suiteBackend.uiText("TOTP_INTRO"); color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                    Text { visible: suiteBackend.totpError !== ""; objectName: "totpError"; text: suiteBackend.totpError; color: "#ee6b80"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10; font.bold: true }
                    Text { visible: suiteBackend.totpMessage !== ""; text: suiteBackend.totpMessage; color: window.green; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10; font.bold: true }
                    Text { visible: suiteBackend.totpStep === "loading"; text: suiteBackend.uiText("TOTP_LOADING"); color: window.muted; font.pixelSize: 10 }
                    Text { visible: suiteBackend.totpStep === "unsupported"; text: suiteBackend.uiText("TOTP_ERR_UNSUPPORTED"); color: window.amber; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                    Text { visible: suiteBackend.totpStep === "off" || suiteBackend.totpStep === "on"; text: suiteBackend.totpStatusText; color: suiteBackend.totpStep === "on" ? window.green : window.muted; font.pixelSize: 10; font.bold: true }

                    ColumnLayout {
                        visible: suiteBackend.totpStep === "off" || suiteBackend.totpStep === "on"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("TOTP_PASSWORD"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        TextField {
                            id: totpPasswordField
                            objectName: "totpPasswordField"
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        Button {
                            objectName: "totpStartButton"
                            visible: suiteBackend.totpStep === "off"
                            text: suiteBackend.uiText("TOTP_START")
                            enabled: !suiteBackend.totpBusy && totpPasswordField.text !== ""
                            onClicked: { suiteBackend.startTotp(totpPasswordField.text); totpPasswordField.text = "" }
                        }
                        Text { visible: suiteBackend.totpStep === "on"; text: suiteBackend.uiText("TOTP_TURN_OFF_CODE"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        TextField {
                            id: totpOffCodeField
                            objectName: "totpOffCodeField"
                            visible: suiteBackend.totpStep === "on"
                            Layout.fillWidth: true
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        Button {
                            objectName: "totpDisableButton"
                            visible: suiteBackend.totpStep === "on"
                            text: suiteBackend.uiText("TOTP_TURN_OFF")
                            enabled: !suiteBackend.totpBusy && totpPasswordField.text !== "" && totpOffCodeField.text !== ""
                            onClicked: { suiteBackend.disableTotp(totpPasswordField.text, totpOffCodeField.text); totpPasswordField.text = ""; totpOffCodeField.text = "" }
                        }
                    }

                    ColumnLayout {
                        visible: suiteBackend.totpStep === "enrolling"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("TOTP_SCAN"); color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                        Canvas {
                            id: totpQrCanvas
                            objectName: "totpQrCanvas"
                            visible: !suiteBackend.totpQr.tooLong
                            Layout.preferredWidth: 176
                            Layout.preferredHeight: 176
                            property var modules: suiteBackend.totpQr.modules
                            onModulesChanged: requestPaint()
                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.fillStyle = "#ffffff"
                                ctx.fillRect(0, 0, width, height)
                                var rows = modules
                                if (!rows || rows.length === 0) return
                                var side = suiteBackend.totpQr.size
                                var cell = width / side
                                ctx.fillStyle = "#000000"
                                for (var r = 0; r < rows.length; r++)
                                    for (var c = 0; c < rows[r].length; c++)
                                        if (rows[r].charAt(c) === "1")
                                            ctx.fillRect((c + 4) * cell, (r + 4) * cell, Math.ceil(cell), Math.ceil(cell))
                            }
                        }
                        Text { visible: suiteBackend.totpQr.tooLong === true; text: suiteBackend.uiText("TOTP_QR_TOO_LONG"); color: window.amber; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                        Text { text: suiteBackend.uiText("TOTP_KEY"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        Text { objectName: "totpKeyText"; text: suiteBackend.totpKey; color: window.cyan; font.family: "Cascadia Mono"; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button { text: suiteBackend.uiText("TOTP_COPY"); onClicked: suiteBackend.copyTotpKey() }
                        Text { text: suiteBackend.uiText("TOTP_CODE"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        TextField {
                            id: totpCodeField
                            objectName: "totpCodeField"
                            Layout.fillWidth: true
                            inputMethodHints: Qt.ImhDigitsOnly
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        RowLayout {
                            spacing: 8
                            Button {
                                objectName: "totpConfirmButton"
                                text: suiteBackend.uiText("TOTP_CONFIRM")
                                enabled: !suiteBackend.totpBusy && totpCodeField.text !== ""
                                onClicked: { suiteBackend.confirmTotp(totpCodeField.text); totpCodeField.text = "" }
                            }
                            Button { text: suiteBackend.uiText("TOTP_CANCEL"); onClicked: suiteBackend.cancelTotp() }
                        }
                    }

                    ColumnLayout {
                        visible: suiteBackend.totpStep === "recovery"
                        Layout.fillWidth: true
                        spacing: 6
                        Text { text: suiteBackend.uiText("TOTP_RECOVERY_TITLE"); color: window.textPrimary; font.bold: true; font.pixelSize: 11 }
                        Text { text: suiteBackend.uiText("TOTP_RECOVERY_HINT"); color: window.amber; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                        Repeater {
                            model: suiteBackend.totpRecovery
                            delegate: Text { required property var modelData; text: modelData; color: window.cyan; font.family: "Cascadia Mono"; font.pixelSize: 13 }
                        }
                        Button { objectName: "totpRecoverySavedButton"; text: suiteBackend.uiText("TOTP_RECOVERY_SAVED"); onClicked: suiteBackend.finishTotp() }
                    }
                }
            }            Item { Layout.fillHeight: true }
        }
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
                                                // Explicit, not left implicit - several real service names in
                                                // this family (HYDRA-UMC-VISUAL-SERVOING-API,
                                                // HYDRA-UMC-SYNTHETIC-DATA-GEN, ...) genuinely wrap to 2 lines
                                                // at this card's own fixed width. A RowLayout doesn't know a
                                                // wrapped Text's real height until after it's already assigned
                                                // that Text its final fillWidth-stretched width, so without this
                                                // it sized itself off the name's un-wrapped single-line height
                                                // and the second line spilled down over the description text
                                                // below it.
                                                Layout.preferredHeight: Math.max(serviceNameText.implicitHeight, healthBadge.implicitHeight)
                                                Text { id: serviceNameText; text: serviceCard.modelData.name; color: window.textPrimary; font.bold: true; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                                Rectangle {
                                                    id: healthBadge
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
                    enabled: suiteBackend.xyTableControlsEnabled
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
                    enabled: suiteBackend.xyTableControlsEnabled
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
                                Text { text: suiteBackend.uiText("QT_XY_TABLE_X_AXIS"); color: window.muted; font.pixelSize: 10 }
                                Text { text: suiteBackend.xyPosX; color: "#f59e0b"; font.family: "Cascadia Mono"; font.pixelSize: 16 }
                                RowLayout {
                                    Button { text: "◀"; onClicked: suiteBackend.jogXyTable("x", -1) }
                                    Button { text: "▶"; onClicked: suiteBackend.jogXyTable("x", 1) }
                                }
                            }
                            ColumnLayout {
                                Text { text: suiteBackend.uiText("QT_XY_TABLE_Y_AXIS"); color: window.muted; font.pixelSize: 10 }
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
                    Text { text: suiteBackend.uiText("LBL_RACK_GEOMETRY_NOTE"); color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Repeater {
                        model: ["width", "depth"]
                        RowLayout {
                            required property string modelData
                            Text { text: suiteBackend.uiText("LBL_RACK_" + modelData.toUpperCase()); color: window.muted }
                            SpinBox {
                                from: 40; to: 1000; stepSize: 1; editable: true
                                value: rackCard.modelData[parent.modelData]
                                onValueModified: suiteBackend.setRackDimension(rackCard.modelData.rackId, parent.modelData, value)
                            }
                        }
                    }
                    RowLayout {
                        Text { text: suiteBackend.uiText("LBL_RACK_COLOR"); color: window.muted }
                        Rectangle { width: 24; height: 24; color: rackCard.modelData.color }
                        TextField {
                            text: rackCard.modelData.color
                            maximumLength: 7
                            validator: RegularExpressionValidator { regularExpression: /#[0-9a-fA-F]{6}/ }
                            onEditingFinished: if (acceptableInput) suiteBackend.setRackColor(rackCard.modelData.rackId, text)
                        }
                    }
                    Button { text: suiteBackend.uiText("LBL_RACK_PREVIEW"); onClicked: suiteBackend.previewRack(rackCard.modelData.rackId) }
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
                                Text { text: suiteBackend.uiText("QT_XY_TABLE_LABEL") + " " + modelData.substring(1).toUpperCase() + " (mm)"; color: "#d97706"; font.pixelSize: 8 }
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
            Rectangle {
                visible: suiteBackend.rackEnabled
                Layout.fillWidth: true
                Layout.preferredHeight: 260
                color: "#ffffff"
                Component.onCompleted: if (visible) suiteBackend.refreshVacuumPreview()
                onVisibleChanged: if (visible) suiteBackend.refreshVacuumPreview()
                Connections {
                    target: suiteBackend
                    function onChanged() { if (suiteBackend.activePanel === "rack") suiteBackend.refreshVacuumPreview() }
                }
                Image {
                    anchors.fill: parent
                    fillMode: Image.PreserveAspectFit
                    cache: false
                    source: suiteBackend.vacuumPreviewVersion > 0 && suiteBackend.vacuumPreviewError === "" ? "image://vacuumFrame/" + suiteBackend.vacuumPreviewVersion : ""
                    MouseArea {
                        anchors.fill: parent
                        property real lastX: 0
                        property real lastY: 0
                        onPressed: function(mouse) { lastX=mouse.x; lastY=mouse.y }
                        onPositionChanged: function(mouse) {
                            if (pressed) suiteBackend.vacuumPreviewOrbit(mouse.x-lastX, mouse.y-lastY)
                            lastX=mouse.x; lastY=mouse.y
                        }
                        onWheel: function(wheel) { suiteBackend.vacuumPreviewZoom(wheel.angleDelta.y > 0 ? .9 : 1.1) }
                    }
                }
                Text { anchors.centerIn: parent; text: suiteBackend.vacuumPreviewError; color: "#991b1b" }
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
                Text { text: suiteBackend.uiText("COL_STATUS"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 210 }
                Text { text: suiteBackend.uiText("COL_SPEED_ACCEL"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 130 }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: suiteBackend.overviewRobots
                delegate: Rectangle {
                    required property var modelData
                    required property int index
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
                        Text { text: modelData.status; color: modelData.motionSource === "live" ? window.green : (modelData.motionSource === "simulated" ? window.amber : window.muted); font.pixelSize: 10; Layout.preferredWidth: 210; elide: Text.ElideRight }
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
                Text { text: suiteBackend.uiText("LBL_MACHINE_ASSETS_NOTE"); color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 260
                    color: "#ffffff"
                    Component.onCompleted: suiteBackend.refreshVacuumPreview()
                    Connections {
                        target: suiteBackend
                        function onChanged() { if (suiteBackend.activePanel === "pick_and_place") suiteBackend.refreshVacuumPreview() }
                    }
                    Image {
                        anchors.fill: parent
                        fillMode: Image.PreserveAspectFit
                        cache: false
                        source: suiteBackend.vacuumPreviewError === "" && suiteBackend.vacuumPreviewVersion > 0 ? "image://vacuumFrame/" + suiteBackend.vacuumPreviewVersion : ""
                        MouseArea {
                            anchors.fill: parent
                            property real lastX: 0
                            property real lastY: 0
                            onPressed: function(mouse) { lastX=mouse.x; lastY=mouse.y }
                            onPositionChanged: function(mouse) {
                                if (pressed) suiteBackend.vacuumPreviewOrbit(mouse.x-lastX, mouse.y-lastY)
                                lastX=mouse.x; lastY=mouse.y
                            }
                            onWheel: function(wheel) { suiteBackend.vacuumPreviewZoom(wheel.angleDelta.y > 0 ? .9 : 1.1) }
                        }
                    }
                    Text { anchors.centerIn: parent; text: suiteBackend.vacuumPreviewError; color: "#991b1b" }
                }
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
                                SpinBox { from: 0; to: suiteBackend.kbsBedCeiling; value: suiteBackend.kbsTargetTemp; editable: true; Layout.preferredWidth: 110; onValueModified: suiteBackend.setKbsTargetTemp(value) }
                                Button {
                                    objectName: "kbsSsrButton"
                                    text: suiteBackend.kbsSsrOn ? suiteBackend.uiText("BTN_SSR_ON") : suiteBackend.uiText("BTN_SSR_OFF")
                                    // Switching the heater on switches 230 V mains: it asks first. Off never asks.
                                    onClicked: suiteBackend.kbsSsrOn
                                        ? suiteBackend.toggleKbsSsr()
                                        : window.requestConfirm(suiteBackend.uiText("LBL_SSR_CONFIRM_TITLE"), suiteBackend.uiText("MSG_SSR_CONFIRM"), function() { suiteBackend.toggleKbsSsr() }, suiteBackend.uiText("BTN_SSR_ON"))
                                }
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
                                // Endstops are inputs read from the machine: shown, never set from here.
                                delegate: Rectangle {
                                    required property var modelData
                                    objectName: "endstop_" + modelData.key
                                    implicitWidth: 120
                                    implicitHeight: 28
                                    radius: 6
                                    color: modelData.active ? "#3a1018" : window.panelAlt
                                    border.width: 1
                                    border.color: modelData.active ? "#ee6b80" : window.panelBorder
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        color: modelData.active ? "#ee6b80" : window.muted
                                        font.pixelSize: 9
                                        font.bold: modelData.active
                                    }
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
    // the former ModuleConfigPanel exactly (robot
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
                        ColumnLayout {
                            visible: suiteBackend.moduleExtraKind === "vacuum_table"
                            Layout.fillWidth: true
                            Text { text: suiteBackend.uiText("LBL_VACUUM_MODEL"); color: window.textPrimary }
                            ComboBox {
                                id: vacuumModelCombo
                                Layout.fillWidth: true
                                model: suiteBackend.vacuumModelOptions
                                textRole: "label"
                                valueRole: "id"
                                Component.onCompleted: currentIndex = indexOfValue(suiteBackend.vacuumModelId)
                                Connections {
                                    target: suiteBackend
                                    function onChanged() { vacuumModelCombo.currentIndex = vacuumModelCombo.indexOfValue(suiteBackend.vacuumModelId) }
                                }
                                onActivated: suiteBackend.selectVacuumModel(currentValue)
                            }
                            Text { text: suiteBackend.uiText("LBL_VACUUM_MODEL_NOTE"); color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                        ColumnLayout {
                            visible: suiteBackend.moduleExtraKind === "heated_bed"
                            Layout.fillWidth: true
                            Text { text: suiteBackend.uiText("LBL_HEATED_MODEL"); color: window.textPrimary }
                            ComboBox {
                                id: heatedModelCombo
                                Layout.fillWidth: true
                                model: suiteBackend.heatedModelOptions
                                textRole: "label"
                                valueRole: "id"
                                Component.onCompleted: currentIndex = indexOfValue(suiteBackend.heatedModelId)
                                Connections {
                                    target: suiteBackend
                                    function onChanged() { heatedModelCombo.currentIndex = heatedModelCombo.indexOfValue(suiteBackend.heatedModelId) }
                                }
                                onActivated: suiteBackend.selectHeatedModel(currentValue)
                            }
                            Text { text: suiteBackend.uiText("LBL_HEATED_MODEL_NOTE"); color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                        RowLayout {
                            spacing: 8
                            Text { text: suiteBackend.uiText("LBL_WIDTH_X"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { from: suiteBackend.moduleExtraKind === "heated_bed" ? 25 : 10; to: 5000; stepSize: ["vacuum_table", "heated_bed"].indexOf(suiteBackend.moduleExtraKind) >= 0 ? 5 : 10; value: suiteBackend.moduleWidth; editable: true; Layout.preferredWidth: 130; onValueModified: suiteBackend.setModuleWidth(value) }
                            Text { text: suiteBackend.uiText("LBL_LENGTH_Y"); color: window.muted; font.pixelSize: 10 }
                            SpinBox { from: suiteBackend.moduleExtraKind === "heated_bed" ? 25 : 10; to: 5000; stepSize: ["vacuum_table", "heated_bed"].indexOf(suiteBackend.moduleExtraKind) >= 0 ? 5 : 10; value: suiteBackend.moduleLength; editable: true; Layout.preferredWidth: 130; onValueModified: suiteBackend.setModuleLength(value) }
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
                            SpinBox { from: 0; to: suiteBackend.moduleBedCeiling; value: suiteBackend.moduleTargetTemp; editable: true; Layout.preferredWidth: 110; onValueModified: suiteBackend.setModuleTargetTemp(value) }
                            Button {
                                objectName: "moduleSsrButton"
                                text: suiteBackend.moduleSsrOn ? suiteBackend.uiText("BTN_SSR_ON") : suiteBackend.uiText("BTN_SSR_OFF")
                                onClicked: suiteBackend.moduleSsrOn
                                    ? suiteBackend.toggleModuleSsr()
                                    : window.requestConfirm(suiteBackend.uiText("LBL_SSR_CONFIRM_TITLE"), suiteBackend.uiText("MSG_SSR_CONFIRM"), function() { suiteBackend.toggleModuleSsr() }, suiteBackend.uiText("BTN_SSR_ON"))
                            }
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
                Rectangle {
                    id: vacuumPreview
                    visible: ["vacuum_table", "heated_bed", "cnc", "laser"].indexOf(suiteBackend.moduleExtraKind) >= 0
                    Layout.fillWidth: true
                    Layout.preferredHeight: 320
                    color: "#ffffff"
                    Text {
                        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                        z: 2
                        visible: ["cnc","laser"].indexOf(suiteBackend.moduleExtraKind) >= 0
                        text: suiteBackend.uiText("LBL_MACHINE_ASSETS_NOTE")
                        color: "#334155"; wrapMode: Text.WordWrap; font.pixelSize: 11
                    }
                    Component.onCompleted: if (visible) suiteBackend.refreshVacuumPreview()
                    onVisibleChanged: if (visible) suiteBackend.refreshVacuumPreview()
                    Connections {
                        target: suiteBackend
                        function onChanged() { if (vacuumPreview.visible) suiteBackend.refreshVacuumPreview() }
                    }
                    Image {
                        anchors.fill: parent
                        fillMode: Image.PreserveAspectFit
                        cache: false
                        source: vacuumPreview.visible && suiteBackend.vacuumPreviewVersion > 0 && suiteBackend.vacuumPreviewError === "" ? "image://vacuumFrame/" + suiteBackend.vacuumPreviewVersion : ""
                        MouseArea {
                            anchors.fill: parent
                            property real lastX: 0
                            property real lastY: 0
                            onPressed: function(mouse) { lastX = mouse.x; lastY = mouse.y }
                            onPositionChanged: function(mouse) {
                                if (pressed) suiteBackend.vacuumPreviewOrbit(mouse.x-lastX, mouse.y-lastY)
                                lastX = mouse.x; lastY = mouse.y
                            }
                            onWheel: function(wheel) { suiteBackend.vacuumPreviewZoom(wheel.angleDelta.y > 0 ? 0.9 : 1.1) }
                        }
                    }
                    Text { anchors.centerIn: parent; width: parent.width-32; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; text: suiteBackend.vacuumPreviewError; color: "#991b1b" }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    // Real 6-joint (+ optional table tx/ty) position editor, reused for
    // both a panel slot's own position AND the revolver's base pickup
    // position - mirrors the former atc_tools panel's reusable PositionEditor
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
    // the former atc_tools panel's AtcGraphicsWidget (QPainter) 1:1 in
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

    // Real MJPEG-fed camera grid - mirrors the former cameras panel's
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

                RowLayout {
                    visible: camCard.modelData.connected
                    spacing: 4
                    Button {
                        text: suiteBackend.uiText("BTN_CAMERA_SNAPSHOT")
                        Layout.fillWidth: true
                        onClicked: suiteBackend.takeCameraSnapshot(camCard.modelData.id)
                    }
                    Button {
                        property bool recording: suiteBackend.cameraRecordingIds.indexOf(camCard.modelData.id) !== -1
                        text: recording ? suiteBackend.uiText("BTN_CAMERA_RECORD_STOP") : suiteBackend.uiText("BTN_CAMERA_RECORD_START")
                        Layout.fillWidth: true
                        onClicked: suiteBackend.toggleCameraRecording(camCard.modelData.id)
                    }
                }
                Text {
                    visible: suiteBackend.cameraCaptureError.length > 0
                    text: suiteBackend.cameraCaptureError
                    color: "#ef4444"
                    font.pixelSize: 8
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
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

    // Real Camera Media panel - QtQuick-mode counterpart to
    // the former CameraMediaPanel (Widgets mode), same
    // real browse/filter/play/delete capability, driven entirely by
    // SuiteQtBridge's cameraMedia* Properties/Slots.
    Component {
        id: cameraMediaComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 10
            Component.onCompleted: suiteBackend.loadCameraMedia()

            RowLayout {
                Text { text: suiteBackend.uiText("CAMERA_MEDIA_TITLE"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16; Layout.fillWidth: true }
                Button { text: suiteBackend.uiText("CAMERA_MEDIA_REFRESH"); onClicked: suiteBackend.loadCameraMedia() }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 4
                Button {
                    text: suiteBackend.uiText("CAMERA_MEDIA_ALL")
                    checkable: true
                    checked: suiteBackend.cameraMediaFilter === "all"
                    onClicked: suiteBackend.setCameraMediaFilter("all")
                }
                Repeater {
                    model: suiteBackend.cameraMediaCameraIds
                    delegate: Button {
                        required property var modelData
                        text: suiteBackend.uiText("LBL_CAM") + " " + modelData
                        checkable: true
                        checked: suiteBackend.cameraMediaFilter === String(modelData)
                        onClicked: suiteBackend.setCameraMediaFilter(String(modelData))
                    }
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                Card {
                    Layout.preferredWidth: 260
                    Layout.fillHeight: true
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            ListView {
                                model: suiteBackend.cameraMediaItems
                                spacing: 2
                                delegate: Rectangle {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: mediaItemText.implicitHeight + 10
                                    color: modelData.isSelected ? "#1a2530" : "transparent"
                                    Text {
                                        id: mediaItemText
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.margins: 6
                                        text: modelData.label
                                        color: window.textPrimary
                                        font.pixelSize: 10
                                        wrapMode: Text.WrapAnywhere
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: suiteBackend.selectCameraMediaItem(modelData.cameraId, modelData.kind, modelData.filename)
                                    }
                                }
                            }
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6

                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Image {
                                id: mediaViewer
                                anchors.fill: parent
                                visible: suiteBackend.cameraMediaImageSource !== ""
                                fillMode: Image.PreserveAspectFit
                                cache: false
                                asynchronous: true
                                source: suiteBackend.cameraMediaImageSource
                            }
                            Rectangle {
                                anchors.fill: parent
                                visible: !mediaViewer.visible
                                color: "#0a0f14"
                                border.width: 1
                                border.color: "#1a2530"
                                Text {
                                    anchors.centerIn: parent
                                    text: suiteBackend.uiText("CAMERA_MEDIA_SELECT_HINT")
                                    color: window.muted
                                    font.pixelSize: 11
                                }
                            }
                        }

                        RowLayout {
                            visible: suiteBackend.cameraMediaHasSelection && suiteBackend.cameraMediaIsRecording
                            spacing: 6
                            Button {
                                text: suiteBackend.cameraMediaPlaying ? suiteBackend.uiText("CAMERA_MEDIA_PAUSE") : suiteBackend.uiText("CAMERA_MEDIA_PLAY")
                                onClicked: suiteBackend.toggleCameraMediaPlay()
                            }
                            Button {
                                text: suiteBackend.uiText("CAMERA_MEDIA_STOP")
                                onClicked: suiteBackend.stopCameraMediaPlay()
                            }
                            Slider {
                                Layout.fillWidth: true
                                from: 0
                                to: Math.max(0, suiteBackend.cameraMediaFrameCount - 1)
                                value: suiteBackend.cameraMediaFrameIndex
                                onMoved: suiteBackend.seekCameraMediaFrame(Math.round(value))
                            }
                            Text {
                                text: (suiteBackend.cameraMediaFrameIndex + 1) + " / " + suiteBackend.cameraMediaFrameCount
                                color: window.muted
                                font.pixelSize: 9
                            }
                        }

                        RowLayout {
                            visible: suiteBackend.cameraMediaHasSelection
                            Item { Layout.fillWidth: true }
                            Button {
                                objectName: "cameraMediaSaveButton"
                                text: suiteBackend.uiText("CAMERA_MEDIA_SAVE_AS")
                                onClicked: cameraMediaSaveDialog.open()
                            }
                            Button {
                                text: suiteBackend.uiText("CAMERA_MEDIA_DELETE")
                                onClicked: cameraMediaDeleteConfirm.open()
                            }
                        }

                        Text {
                            visible: suiteBackend.cameraMediaError.length > 0
                            text: suiteBackend.cameraMediaError
                            color: "#ef4444"
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            FileDialog {
                id: cameraMediaSaveDialog
                title: suiteBackend.uiText("CAMERA_MEDIA_SAVE_AS")
                fileMode: FileDialog.SaveFile
                onAccepted: suiteBackend.saveCameraMedia(selectedFile.toString())
            }

            MessageDialog {
                id: cameraMediaDeleteConfirm
                text: suiteBackend.uiText("CAMERA_MEDIA_DELETE_CONFIRM")
                buttons: MessageDialog.Yes | MessageDialog.No
                onButtonClicked: function (button, role) {
                    if (button === MessageDialog.Yes) suiteBackend.deleteCameraMediaSelected()
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
    // flasher - mirrors the former FlasherPanel 1:1 (mock
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

    // Real CAN-OTA runtime diagnostics - mirrors the former tester panel's
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
                    // Explicit, not left implicit - see the ecosystem
                    // services card's own comment above for why a wrapped
                    // sibling Text needs its RowLayout height bound to its
                    // own real implicitHeight instead of left to the row's
                    // un-wrapped default. This note text is long enough to
                    // wrap at this row's own width, and was spilling down
                    // over the button next to it.
                    Layout.preferredHeight: Math.max(selfTestNoteText.implicitHeight, selfTestButton.implicitHeight)
                    Text { id: selfTestNoteText; text: suiteBackend.uiText("LBL_SELF_TEST_NOTE"); color: window.muted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Button {
                        id: selfTestButton
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
    // the former ViewportPanel/RobotViewport 1:1. The one
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
                        // anchors.fill + margins, not anchors.centerIn plus
                        // an arithmetic `width: parent.width - 40` - the
                        // exact same real pattern found (and confirmed
                        // broken with a real on-screen check, not just a
                        // theory) in HYDRA-UMC-EDITOR-URDF's own structurally
                        // identical viewport-unavailable message: that
                        // expression can freeze at whatever width its parent
                        // happened to have at component-completion and never
                        // re-evaluate afterward, wrapping this message one
                        // word per line in a sliver a few pixels wide.
                        // Anchoring directly to the real, continuously
                        // -updated parent geometry doesn't have that failure
                        // mode.
                        anchors.fill: parent
                        anchors.margins: 20
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
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

    // A small line chart drawn on a Canvas: one polyline per series (a null value leaves a gap), scaled to
    // 0..maxValue, or to the largest value when maxValue is 0.
    component LineChart: Canvas {
        id: chart
        property var seriesList: []
        property var colors: []
        property var dashed: []
        property real maxValue: 0
        property string unit: ""
        onSeriesListChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.fillStyle = "#0d1117"
            ctx.fillRect(0, 0, width, height)
            var top = maxValue
            if (top <= 0) {
                top = 1
                for (var s0 = 0; s0 < seriesList.length; s0++)
                    for (var i0 = 0; i0 < seriesList[s0].length; i0++)
                        if (seriesList[s0][i0] !== null && seriesList[s0][i0] > top) top = seriesList[s0][i0]
            }
            ctx.strokeStyle = "#1e293b"
            ctx.lineWidth = 1
            for (var g = 0; g <= 4; g++) {
                var gy = Math.round(4 + (height - 8) * g / 4) + 0.5
                ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(width, gy); ctx.stroke()
            }
            ctx.fillStyle = "#64748b"
            ctx.font = "9px sans-serif"
            ctx.fillText(Math.round(top) + chart.unit, 4, 12)
            ctx.fillText("0", 4, height - 3)
            for (var s = 0; s < seriesList.length; s++) {
                var data = seriesList[s]
                var count = data.length
                if (count < 2) continue
                ctx.strokeStyle = colors[s] || "#22d3ee"
                ctx.lineWidth = dashed[s] ? 1 : 2
                ctx.setLineDash(dashed[s] ? [4, 3] : [])
                ctx.beginPath()
                var pen = false
                for (var i = 0; i < count; i++) {
                    var v = data[i]
                    if (v === null || v === undefined) { pen = false; continue }
                    var x = 4 + (width - 8) * i / (count - 1)
                    var y = 4 + (height - 8) * (1 - Math.min(v, top) / top)
                    if (!pen) { ctx.moveTo(x, y); pen = true } else ctx.lineTo(x, y)
                }
                ctx.stroke()
            }
        }
    }

    component StatTile: Card {
        id: tile
        property string label: ""
        property string value: "-"
        property string sub: ""
        Layout.preferredHeight: 74
        Layout.fillWidth: true
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 1
            Text { text: tile.label; color: window.muted; font.pixelSize: 9; font.bold: true }
            Text { text: tile.value; color: window.textPrimary; font.family: "Cascadia Mono"; font.pixelSize: 18; font.bold: true }
            Text { text: tile.sub; color: "#556070"; font.family: "Cascadia Mono"; font.pixelSize: 9 }
        }
    }

    Component {
        id: robotsCatalogComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 10
            Text { text: suiteBackend.uiText("DOCK_ROBOTS_CATALOG"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1
                    Rectangle { anchors.fill: parent; color: "#0a0f14"; border.width: 1; border.color: "#1a2530" }
                    Image {
                        id: catalogImage
                        anchors.fill: parent
                        fillMode: Image.PreserveAspectFit
                        cache: false
                        asynchronous: true
                        visible: suiteBackend.catalogPreviewError === "" && suiteBackend.catalogPreviewVersion > 0
                        source: visible ? ("image://catalogFrame/" + suiteBackend.catalogPreviewVersion) : ""
                        MouseArea {
                            anchors.fill: parent
                            property real lastX: 0
                            property real lastY: 0
                            onPressed: function(mouse) { lastX = mouse.x; lastY = mouse.y }
                            onPositionChanged: function(mouse) {
                                suiteBackend.catalogPreviewOrbit(mouse.x - lastX, mouse.y - lastY)
                                lastX = mouse.x; lastY = mouse.y
                            }
                            onWheel: function(wheel) { suiteBackend.catalogPreviewZoom(wheel.angleDelta.y > 0 ? 0.9 : 1.1) }
                        }
                    }
                    Text {
                        anchors.fill: parent
                        anchors.margins: 20
                        visible: !catalogImage.visible
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.WordWrap
                        text: suiteBackend.catalogPreviewError
                        color: window.muted
                    }
                    Component.onCompleted: suiteBackend.refreshCatalogPreview()
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        ComboBox {
                            Layout.fillWidth: true
                            model: suiteBackend.catalogManufacturers
                            textRole: "label"
                            valueRole: "value"
                            onActivated: suiteBackend.setCatalogManufacturer(currentValue)
                        }
                        ComboBox {
                            Layout.preferredWidth: 130
                            model: [suiteBackend.uiText("OPT_ALL_DOF"), "5-DOF", "6-DOF"]
                            onActivated: suiteBackend.setCatalogDof(currentIndex === 1 ? 5 : (currentIndex === 2 ? 6 : 0))
                        }
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 3
                        model: suiteBackend.catalogRows
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            height: 34
                            radius: 8
                            color: modelData.selected ? "#1a4967" : window.panelAlt
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                CheckBox {
                                    checked: modelData.enabled
                                    onToggled: suiteBackend.setCatalogModelEnabled(modelData.model, checked)
                                }
                                Text { text: modelData.model; color: window.textPrimary; font.pixelSize: 11; font.bold: modelData.selected; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: modelData.manufacturer; color: window.muted; font.pixelSize: 10 }
                            }
                            MouseArea {
                                anchors.fill: parent
                                anchors.leftMargin: 40
                                onClicked: suiteBackend.selectCatalogModel(modelData.model)
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: ecosystemHealthComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Text { text: suiteBackend.uiText("DOCK_ECOSYSTEM_HEALTH"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                Button { objectName: "ecoHealthRefresh"; text: suiteBackend.uiText("ECOHEALTH_REFRESH"); onClicked: suiteBackend.refreshEcoHealth() }
            }
            Text { text: suiteBackend.uiText("ECOHEALTH_DESC"); color: "#556070"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { objectName: "ecoHealthProblem"; visible: suiteBackend.ecoHealthStatus !== ""; text: suiteBackend.ecoHealthStatus; color: "#ee6b80"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { visible: !suiteBackend.ecoHealthLoaded && suiteBackend.ecoHealthStatus === ""; text: suiteBackend.uiText("ECOHEALTH_LOADING"); color: "#556070"; font.pixelSize: 11 }
            Text { visible: suiteBackend.ecoHealthUnavailable; text: suiteBackend.uiText("ECOHEALTH_NOT_AVAILABLE"); color: window.amber; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Repeater {
                model: suiteBackend.ecoHealthNotices
                delegate: Text {
                    required property var modelData
                    objectName: "ecoHealthNotice"
                    text: modelData.text
                    color: modelData.level === "error" ? "#ee6b80" : (modelData.level === "warn" ? window.amber : window.muted)
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }
            Flow {
                Layout.fillWidth: true
                spacing: 6
                Repeater {
                    model: suiteBackend.ecoHealthFilters
                    delegate: Button {
                        required property var modelData
                        objectName: "ecoHealthFilter_" + modelData.key
                        text: modelData.label
                        checkable: true
                        checked: modelData.selected
                        onClicked: suiteBackend.setEcoHealthFilter(modelData.key)
                    }
                }
            }
            Text { visible: suiteBackend.ecoHealthEmpty !== ""; text: suiteBackend.ecoHealthEmpty; color: "#556070"; font.pixelSize: 11 }
            ListView {
                objectName: "ecoHealthList"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: suiteBackend.ecoHealthCards
                spacing: 6
                delegate: Card {
                    required property var modelData
                    width: ListView.view.width
                    height: 76
                    border.color: modelData.state === "down" ? "#ee6b80" : (modelData.state === "degraded" ? window.amber : window.panelBorder)
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: modelData.name; color: window.textPrimary; font.bold: true; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text { text: modelData.stateLabel; color: modelData.state === "ok" ? window.green : (modelData.state === "down" ? "#ee6b80" : (modelData.state === "degraded" ? window.amber : window.muted)); font.bold: true; font.pixelSize: 10 }
                        }
                        Text { visible: modelData.reason !== ""; text: modelData.reason; color: window.muted; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: modelData.versions; color: "#556070"; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text { visible: modelData.drift; text: modelData.driftLabel; color: window.amber; font.bold: true; font.pixelSize: 9 }
                        }
                        Text { text: modelData.seen; color: "#556070"; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                }
            }
        }
    }

    Component {
        id: supervisorComponent
        ScrollView {
            id: supervisorScroll
            width: contentLoader.width
            height: contentLoader.height
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                id: supervisorBody
                width: supervisorScroll.availableWidth
                spacing: 10
                property var view: suiteBackend.supervisorView
                property var ver: suiteBackend.supervisorVersion
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    Text { text: suiteBackend.uiText("HEADING_SYSTEM_SUPERVISOR"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                    Item { Layout.fillWidth: true }
                    Text { text: suiteBackend.supervisorLive; color: window.muted; font.pixelSize: 10 }
                    Text { text: supervisorBody.view.uptime ? supervisorBody.view.uptime : ""; color: window.muted; font.pixelSize: 10 }
                    Repeater {
                        model: [
                            { name: suiteBackend.uiText("LBL_SUPERVISOR_WIFI"), state: supervisorBody.view.wifi },
                            { name: suiteBackend.uiText("LBL_SUPERVISOR_BLUETOOTH"), state: supervisorBody.view.bluetooth },
                            { name: suiteBackend.uiText("LBL_SUPERVISOR_ETHERNET"), state: supervisorBody.view.ethernet }
                        ]
                        delegate: Text {
                            required property var modelData
                            text: modelData.name
                            font.pixelSize: 9
                            font.bold: true
                            color: modelData.state === "on" ? window.green : (modelData.state === "off" ? "#e05050" : "#3a4250")
                        }
                    }
                }
                Text { visible: suiteBackend.supervisorStatus !== ""; text: suiteBackend.supervisorStatus; color: window.amber; font.pixelSize: 11 }
                GridLayout {
                    Layout.fillWidth: true
                    columns: 6
                    columnSpacing: 8
                    Repeater {
                        model: supervisorBody.view.tiles ? supervisorBody.view.tiles : []
                        delegate: StatTile {
                            required property var modelData
                            label: modelData.label
                            value: modelData.value
                            sub: modelData.sub
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Card {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 190
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Text { text: suiteBackend.uiText("LBL_SUPERVISOR_CPU_TREND"); color: window.muted; font.pixelSize: 9; font.bold: true }
                            LineChart {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                maxValue: 100
                                unit: "%"
                                colors: ["#22d3ee"]
                                seriesList: supervisorBody.view.cpuSeries ? [supervisorBody.view.cpuSeries] : []
                            }
                        }
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 190
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 3
                            Text { text: suiteBackend.uiText("LBL_SUPERVISOR_CPU_CORES"); color: window.muted; font.pixelSize: 9; font.bold: true }
                            Flickable {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                contentHeight: coresColumn.implicitHeight
                                ColumnLayout {
                                    id: coresColumn
                                    width: parent.width
                                    spacing: 3
                                    Repeater {
                                        model: supervisorBody.view.cores ? supervisorBody.view.cores : []
                                        delegate: RowLayout {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            Text { text: modelData.name; color: window.muted; font.pixelSize: 9; Layout.preferredWidth: 24 }
                                            ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: modelData.percent }
                                            Text { text: modelData.frequency; color: "#556070"; font.family: "Cascadia Mono"; font.pixelSize: 9; Layout.preferredWidth: 64; horizontalAlignment: Text.AlignRight }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Card {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 170
                        visible: supervisorBody.view.hasMemory === true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Text { text: suiteBackend.uiText("LBL_SUPERVISOR_MEMORY_TREND"); color: window.muted; font.pixelSize: 9; font.bold: true }
                            LineChart {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                maxValue: 100
                                unit: "%"
                                colors: ["#fbbf24", "#94a3b8"]
                                dashed: [false, true]
                                seriesList: supervisorBody.view.memUsedSeries ? [supervisorBody.view.memUsedSeries, supervisorBody.view.memCachedSeries] : []
                            }
                        }
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 170
                        visible: supervisorBody.view.hasTemps === true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Text { text: suiteBackend.uiText("LBL_SUPERVISOR_TEMP_TREND"); color: window.muted; font.pixelSize: 9; font.bold: true }
                            LineChart {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                unit: "°C"
                                colors: ["#fb7185", "#f472b6"]
                                seriesList: supervisorBody.view.cpuTempSeries ? [supervisorBody.view.cpuTempSeries, supervisorBody.view.rp1TempSeries] : []
                            }
                        }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: supervisorBody.view.hasTraffic === true
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        StatTile {
                            visible: supervisorBody.view.wifiTotal !== undefined && supervisorBody.view.wifiTotal !== null
                            label: suiteBackend.uiText("LBL_SUPERVISOR_WIFI_TOTAL")
                            value: supervisorBody.view.wifiTotal ? supervisorBody.view.wifiTotal.total : "-"
                            sub: supervisorBody.view.wifiTotal ? supervisorBody.view.wifiTotal.sub : ""
                        }
                        StatTile {
                            visible: supervisorBody.view.ethernetTotal !== undefined && supervisorBody.view.ethernetTotal !== null
                            label: suiteBackend.uiText("LBL_SUPERVISOR_ETHERNET_TOTAL")
                            value: supervisorBody.view.ethernetTotal ? supervisorBody.view.ethernetTotal.total : "-"
                            sub: supervisorBody.view.ethernetTotal ? supervisorBody.view.ethernetTotal.sub : ""
                        }
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 170
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Text { text: suiteBackend.uiText("LBL_SUPERVISOR_NETWORK_THROUGHPUT"); color: window.muted; font.pixelSize: 9; font.bold: true }
                            LineChart {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                unit: " B/s"
                                colors: ["#38bdf8", "#38bdf8", "#fbbf24", "#fbbf24"]
                                dashed: [false, true, false, true]
                                seriesList: supervisorBody.view.rates ? [supervisorBody.view.rates.wifiRx, supervisorBody.view.rates.wifiTx, supervisorBody.view.rates.ethRx, supervisorBody.view.rates.ethTx] : []
                            }
                        }
                    }
                }
                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 60 + 24 * (supervisorBody.view.processes ? supervisorBody.view.processes.length : 0)
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4
                        Text { text: suiteBackend.uiText("LBL_SUPERVISOR_PROCESSES"); color: window.muted; font.pixelSize: 9; font.bold: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: suiteBackend.uiText("COL_SUPERVISOR_PID"); color: window.muted; font.pixelSize: 9; Layout.preferredWidth: 70 }
                            Text { text: suiteBackend.uiText("COL_SUPERVISOR_PROCESS"); color: window.muted; font.pixelSize: 9; Layout.fillWidth: true }
                            Text { text: suiteBackend.uiText("COL_SUPERVISOR_CPU_PERCENT"); color: window.muted; font.pixelSize: 9; Layout.preferredWidth: 70 }
                            Text { text: suiteBackend.uiText("COL_SUPERVISOR_MEM_PERCENT"); color: window.muted; font.pixelSize: 9; Layout.preferredWidth: 70 }
                            Text { text: suiteBackend.uiText("COL_SUPERVISOR_RSS"); color: window.muted; font.pixelSize: 9; Layout.preferredWidth: 80 }
                        }
                        Repeater {
                            model: supervisorBody.view.processes ? supervisorBody.view.processes : []
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                Text { text: modelData.pid; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 70 }
                                Text { text: modelData.name; color: window.textPrimary; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: modelData.cpu; color: window.textPrimary; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 70 }
                                Text { text: modelData.mem; color: window.textPrimary; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 70 }
                                Text { text: modelData.rss; color: window.textPrimary; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 80 }
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: safetyLimitsComponent
        ScrollView {
            id: safetyScroll
            width: contentLoader.width
            height: contentLoader.height
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                id: safetyBody
                width: safetyScroll.availableWidth
                spacing: 12
                // The values being edited. They follow the server until the administrator touches something.
                property var form: suiteBackend.safetyForm
                property bool dirty: false
                property var hard: suiteBackend.safetyHard
                property string newModel: ""
                function edit(patch) {
                    var next = Object.assign({}, safetyBody.form, patch)
                    safetyBody.form = next
                    safetyBody.dirty = true
                }
                function editRow(index, patch) {
                    var rows = safetyBody.form.rows.slice()
                    rows[index] = Object.assign({}, rows[index], patch)
                    edit({ rows: rows })
                }
                Connections {
                    target: suiteBackend
                    function onChanged() {
                        if (suiteBackend.safetyMessage !== "") safetyBody.dirty = false
                        if (!safetyBody.dirty) safetyBody.form = suiteBackend.safetyForm
                        safetyBody.hard = suiteBackend.safetyHard
                    }
                }
                Text { text: suiteBackend.uiText("HEADING_SAFETY_LIMITS"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
                Text {
                    visible: !suiteBackend.safetyHasServer
                    text: suiteBackend.uiText("LBL_ES_NO_ACTIVE_SERVER")
                    color: window.muted
                }
                Text {
                    visible: suiteBackend.safetyHasServer && !suiteBackend.safetyIsAdmin
                    text: suiteBackend.uiText("MSG_SAFETY_ADMIN_ONLY")
                    color: window.amber
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                ColumnLayout {
                    visible: suiteBackend.safetyHasServer && suiteBackend.safetyIsAdmin
                    Layout.fillWidth: true
                    spacing: 12
                    Text { text: suiteBackend.uiText("MSG_SAFETY_INTRO"); color: window.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Card {
                        Layout.fillWidth: true
                        Layout.preferredHeight: armColumn.implicitHeight + 28
                        ColumnLayout {
                            id: armColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            Text { text: suiteBackend.uiText("GROUP_SAFETY_ARMING"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                            CheckBox {
                                id: armRequiredBox
                                objectName: "armRequiredBox"
                                text: suiteBackend.uiText("LBL_SAFETY_ARM_REQUIRED")
                                checked: safetyBody.form.armRequired === true
                                onToggled: safetyBody.edit({ armRequired: checked })
                                palette.windowText: window.textPrimary
                            }
                            Text { text: suiteBackend.uiText("HINT_SAFETY_ARM_REQUIRED"); color: "#556070"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            RowLayout {
                                spacing: 8
                                Text { text: suiteBackend.uiText("LBL_SAFETY_ARM_TTL"); color: window.muted; Layout.preferredWidth: 260 }
                                TextField {
                                    objectName: "armTtlField"
                                    text: safetyBody.form.armTtlSeconds !== undefined ? safetyBody.form.armTtlSeconds : ""
                                    onTextEdited: safetyBody.edit({ armTtlSeconds: text })
                                    Layout.preferredWidth: 90
                                    color: window.textPrimary
                                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                                }
                                Text { text: suiteBackend.uiText("LBL_SAFETY_BETWEEN") + " " + safetyBody.hard.armTtlMinS + " - " + safetyBody.hard.armTtlMaxS; color: "#556070"; font.pixelSize: 10 }
                            }
                            CheckBox {
                                id: requireControllerBox
                                objectName: "requireControllerBox"
                                text: suiteBackend.uiText("LBL_SAFETY_REQUIRE_CONTROLLER")
                                checked: safetyBody.form.requireControllerId === true
                                onToggled: safetyBody.edit({ requireControllerId: checked })
                                palette.windowText: window.textPrimary
                            }
                            Text { text: suiteBackend.uiText("HINT_SAFETY_REQUIRE_CONTROLLER"); color: "#556070"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.preferredHeight: limitsColumn.implicitHeight + 28
                        ColumnLayout {
                            id: limitsColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 6
                            Text { text: suiteBackend.uiText("GROUP_SAFETY_LIMITS"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                            Text {
                                text: suiteBackend.uiText("HINT_SAFETY_CEILINGS") + " " + safetyBody.hard.jogMaxAmount + " / " + safetyBody.hard.jogMaxAbsolute + " / " + safetyBody.hard.bedMaxC + " °C"
                                color: "#556070"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Text { text: suiteBackend.uiText("COL_SAFETY_MODEL"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 150 }
                                Text { text: suiteBackend.uiText("COL_SAFETY_JOG_RELATIVE"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 130 }
                                Text { text: suiteBackend.uiText("COL_SAFETY_JOG_ABSOLUTE"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 130 }
                                Text { text: suiteBackend.uiText("COL_SAFETY_BED"); color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 130 }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Text { text: suiteBackend.uiText("LBL_SAFETY_DEFAULT_ROW"); color: window.textPrimary; font.bold: true; Layout.preferredWidth: 150 }
                                TextField {
                                    objectName: "defaultAmountField"
                                    text: safetyBody.form.defaultMaxAmount !== undefined ? safetyBody.form.defaultMaxAmount : ""
                                    onTextEdited: safetyBody.edit({ defaultMaxAmount: text })
                                    Layout.preferredWidth: 130; color: window.textPrimary
                                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                                }
                                TextField {
                                    text: safetyBody.form.defaultMaxAbsolute !== undefined ? safetyBody.form.defaultMaxAbsolute : ""
                                    onTextEdited: safetyBody.edit({ defaultMaxAbsolute: text })
                                    Layout.preferredWidth: 130; color: window.textPrimary
                                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                                }
                                TextField {
                                    text: safetyBody.form.defaultBedMaxC !== undefined ? safetyBody.form.defaultBedMaxC : ""
                                    onTextEdited: safetyBody.edit({ defaultBedMaxC: text })
                                    Layout.preferredWidth: 130; color: window.textPrimary
                                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                                }
                            }
                            Repeater {
                                model: safetyBody.form.rows ? safetyBody.form.rows : []
                                delegate: RowLayout {
                                    id: modelRow
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Text { text: modelRow.modelData.model; color: window.textPrimary; font.family: "Cascadia Mono"; Layout.preferredWidth: 150; elide: Text.ElideRight }
                                    TextField {
                                        text: modelRow.modelData.maxAmount
                                        placeholderText: suiteBackend.uiText("LBL_SAFETY_INHERIT")
                                        onTextEdited: safetyBody.editRow(modelRow.index, { maxAmount: text })
                                        Layout.preferredWidth: 130; color: window.textPrimary
                                        background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                                    }
                                    TextField {
                                        text: modelRow.modelData.maxAbsolute
                                        placeholderText: suiteBackend.uiText("LBL_SAFETY_INHERIT")
                                        onTextEdited: safetyBody.editRow(modelRow.index, { maxAbsolute: text })
                                        Layout.preferredWidth: 130; color: window.textPrimary
                                        background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                                    }
                                    TextField {
                                        text: modelRow.modelData.bedMaxC
                                        placeholderText: suiteBackend.uiText("LBL_SAFETY_INHERIT")
                                        onTextEdited: safetyBody.editRow(modelRow.index, { bedMaxC: text })
                                        Layout.preferredWidth: 130; color: window.textPrimary
                                        background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                                    }
                                    Button {
                                        text: "×"
                                        implicitHeight: 26
                                        Accessible.name: suiteBackend.uiText("BTN_SAFETY_REMOVE_MODEL")
                                        onClicked: {
                                            var rows = safetyBody.form.rows.slice()
                                            rows.splice(modelRow.index, 1)
                                            safetyBody.edit({ rows: rows })
                                        }
                                    }
                                }
                            }
                            RowLayout {
                                spacing: 6
                                TextField {
                                    id: newModelField
                                    objectName: "newModelField"
                                    placeholderText: suiteBackend.uiText("PLACEHOLDER_SAFETY_MODEL")
                                    Layout.preferredWidth: 260
                                    color: window.textPrimary
                                    background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                                }
                                Button {
                                    text: suiteBackend.uiText("BTN_SAFETY_ADD_MODEL")
                                    onClicked: {
                                        var name = newModelField.text.trim()
                                        if (name === "") return
                                        var rows = safetyBody.form.rows.slice()
                                        rows.push({ model: name, maxAmount: "", maxAbsolute: "", bedMaxC: "" })
                                        safetyBody.edit({ rows: rows })
                                        newModelField.text = ""
                                    }
                                }
                            }
                        }
                    }
                    RowLayout {
                        spacing: 10
                        Button {
                            objectName: "safetySaveButton"
                            text: suiteBackend.uiText("BTN_SAFETY_SAVE")
                            enabled: safetyBody.dirty
                            onClicked: suiteBackend.saveSafetyLimits(safetyBody.form)
                        }
                        Button {
                            text: suiteBackend.uiText("BTN_SAFETY_DEFAULTS")
                            onClicked: { safetyBody.form = suiteBackend.safetyDefaultsForm(); safetyBody.dirty = true }
                        }
                        Text { visible: suiteBackend.safetyMessage !== ""; text: suiteBackend.safetyMessage; color: window.green; font.bold: true; font.pixelSize: 11 }
                        Text { visible: suiteBackend.safetyError !== ""; text: suiteBackend.safetyError; color: "#ee6b80"; font.bold: true; font.pixelSize: 11 }
                    }
                }
            }
        }
    }

    Component {
        id: auditRecordComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 8
            Text { text: suiteBackend.uiText("HEADING_AUDIT_RECORD"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            Text {
                visible: !suiteBackend.auditHasServer
                text: suiteBackend.uiText("LBL_ES_NO_ACTIVE_SERVER")
                color: window.muted
            }
            Text {
                visible: suiteBackend.auditHasServer && !suiteBackend.auditIsAdmin
                text: suiteBackend.uiText("AUDIT_ADMIN_ONLY")
                color: window.amber
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            ColumnLayout {
                visible: suiteBackend.auditHasServer && suiteBackend.auditIsAdmin
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8
                Text { text: suiteBackend.uiText("AUDIT_INTRO"); color: window.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    ComboBox {
                        id: auditTypeCombo
                        objectName: "auditTypeCombo"
                        Layout.preferredWidth: 220
                        model: suiteBackend.auditTypeOptions
                        textRole: "label"
                        valueRole: "value"
                        Component.onCompleted: currentIndex = indexOfValue(suiteBackend.auditType)
                        onActivated: suiteBackend.setAuditType(currentValue)
                    }
                    ComboBox {
                        id: auditRobotCombo
                        objectName: "auditRobotCombo"
                        Layout.preferredWidth: 220
                        model: suiteBackend.auditRobotOptions
                        textRole: "label"
                        valueRole: "value"
                        Component.onCompleted: currentIndex = Math.max(0, indexOfValue(suiteBackend.auditRobot))
                        onActivated: suiteBackend.setAuditRobot(currentValue)
                    }
                    ComboBox {
                        id: auditLimitCombo
                        Layout.preferredWidth: 100
                        model: suiteBackend.auditLimits
                        Component.onCompleted: currentIndex = model.indexOf(suiteBackend.auditLimit)
                        onActivated: suiteBackend.setAuditLimit(model[currentIndex])
                        ToolTip.visible: hovered
                        ToolTip.text: suiteBackend.uiText("AUDIT_FILTER_LIMIT")
                    }
                    Button { objectName: "auditRefreshButton"; text: suiteBackend.uiText("AUDIT_REFRESH"); enabled: !suiteBackend.auditBusy; onClicked: suiteBackend.refreshAudit() }
                    Button { objectName: "auditVerifyButton"; text: suiteBackend.uiText("AUDIT_VERIFY"); enabled: !suiteBackend.auditBusy; onClicked: suiteBackend.verifyAudit() }
                    Button { objectName: "auditExportButton"; text: suiteBackend.uiText("AUDIT_EXPORT"); enabled: !suiteBackend.auditBusy; onClicked: auditExportDialog.open() }
                }
                Text { visible: suiteBackend.auditMessage !== ""; text: suiteBackend.auditMessage; color: window.green; font.bold: true; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { visible: suiteBackend.auditError !== ""; text: suiteBackend.auditError; color: "#ee6b80"; font.bold: true; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Repeater {
                    model: suiteBackend.auditChain
                    delegate: Text {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.text
                        color: modelData.ok ? window.green : "#ee6b80"
                        font.bold: true
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: suiteBackend.uiText("AUDIT_COL_SEQ"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 40 }
                    Text { text: suiteBackend.uiText("AUDIT_COL_TIME"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 130 }
                    Text { text: suiteBackend.uiText("AUDIT_COL_TYPE"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 130 }
                    Text { text: suiteBackend.uiText("AUDIT_COL_OUTCOME"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 70 }
                    Text { text: suiteBackend.uiText("AUDIT_COL_ACCOUNT"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 90 }
                    Text { text: suiteBackend.uiText("AUDIT_COL_CONTROLLER"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 110 }
                    Text { text: suiteBackend.uiText("AUDIT_COL_ADDRESS"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 100 }
                    Text { text: suiteBackend.uiText("AUDIT_COL_ROBOT"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 90 }
                    Text { text: suiteBackend.uiText("AUDIT_COL_DETAIL"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.fillWidth: true }
                }
                ListView {
                    objectName: "auditList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: suiteBackend.auditRows
                    delegate: RowLayout {
                        required property var modelData
                        width: ListView.view.width
                        spacing: 8
                        Text { text: modelData.seq; color: "#556070"; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 40 }
                        Text { text: modelData.time; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 130 }
                        Text { text: modelData.type; color: window.textPrimary; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 130; elide: Text.ElideRight }
                        Text { text: modelData.outcome; color: modelData.outcomeKind === "ok" ? window.green : (modelData.outcomeKind === "refused" ? window.amber : "#ee6b80"); font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 70 }
                        Text { text: modelData.account; color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 90; elide: Text.ElideRight }
                        Text { text: modelData.controller; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 110; elide: Text.ElideRight }
                        Text { text: modelData.address; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 100; elide: Text.ElideRight }
                        Text { text: modelData.robot; color: window.muted; font.pixelSize: 10; Layout.preferredWidth: 90; elide: Text.ElideRight }
                        Text { text: modelData.detail; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                }
            }
        }
    }

    Component {
        id: usersComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 8
            Dialog {
                id: usersDeleteDialog
                property string target: ""
                anchors.centerIn: Overlay.overlay
                modal: true
                width: 380
                title: suiteBackend.uiText("USERS_DELETE_TITLE")
                standardButtons: Dialog.Yes | Dialog.No
                background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
                contentItem: Text { text: suiteBackend.uiText("USERS_DELETE_CONFIRM").replace("{username}", usersDeleteDialog.target); color: window.textPrimary; wrapMode: Text.WordWrap }
                onAccepted: suiteBackend.deleteUser(usersDeleteDialog.target)
            }
            Dialog {
                id: totpResetDialog
                property string target: ""
                anchors.centerIn: Overlay.overlay
                modal: true
                width: 380
                title: suiteBackend.uiText("TOTP_RESET_BUTTON")
                standardButtons: Dialog.Yes | Dialog.No
                background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
                contentItem: Text { text: suiteBackend.uiText("TOTP_RESET_CONFIRM").replace("{username}", totpResetDialog.target); color: window.textPrimary; wrapMode: Text.WordWrap }
                onAccepted: suiteBackend.resetUserTotp(totpResetDialog.target)
            }
            Text { text: suiteBackend.uiText("HEADING_USERS"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            Text {
                visible: !suiteBackend.usersHasServer
                text: suiteBackend.uiText("LBL_ES_NO_ACTIVE_SERVER")
                color: window.muted
            }
            Text {
                visible: suiteBackend.usersHasServer && !suiteBackend.usersIsAdmin
                text: suiteBackend.uiText("USERS_ADMIN_ONLY")
                color: window.amber
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            ColumnLayout {
                visible: suiteBackend.usersHasServer && suiteBackend.usersIsAdmin
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8
                Text { text: suiteBackend.uiText("USERS_INTRO"); color: window.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { visible: suiteBackend.usersMessage !== ""; text: suiteBackend.usersMessage; color: window.green; font.bold: true; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { visible: suiteBackend.usersError !== ""; text: suiteBackend.usersError; color: "#ee6b80"; font.bold: true; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: suiteBackend.uiText("USERS_COL_USERNAME"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 180 }
                    Text { text: suiteBackend.uiText("USERS_COL_ROLE"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 110 }
                    Text { text: suiteBackend.uiText("USERS_COL_CREATED"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.fillWidth: true }
                    Button { objectName: "usersRefreshButton"; text: suiteBackend.uiText("USERS_REFRESH"); enabled: !suiteBackend.usersBusy; onClicked: suiteBackend.refreshUsers() }
                }
                ListView {
                    objectName: "usersList"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 170
                    clip: true
                    model: suiteBackend.usersRows
                    delegate: RowLayout {
                        required property var modelData
                        width: ListView.view.width
                        spacing: 8
                        Text { text: modelData.username + (modelData.own ? " (" + suiteBackend.uiText("USERS_YOU") + ")" : ""); color: window.textPrimary; font.bold: true; font.pixelSize: 11; Layout.preferredWidth: 180; elide: Text.ElideRight }
                        Text { text: modelData.roleLabel; color: modelData.role === "admin" ? window.green : window.cyan; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 110 }
                        Text { text: modelData.created; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                        Button {
                            objectName: "usersTotpResetButton"
                            text: suiteBackend.uiText("TOTP_RESET_BUTTON")
                            enabled: !suiteBackend.usersBusy
                            onClicked: { totpResetDialog.target = modelData.username; totpResetDialog.open() }
                        }
                        Button {
                            objectName: "usersDeleteButton"
                            text: suiteBackend.uiText("USERS_DELETE")
                            enabled: !suiteBackend.usersBusy
                            onClicked: { usersDeleteDialog.target = modelData.username; usersDeleteDialog.open() }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        spacing: 6
                        Text { text: suiteBackend.uiText("USERS_CHANGE_TITLE"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                        ComboBox {
                            id: usersChangeAccount
                            objectName: "usersChangeAccount"
                            Layout.fillWidth: true
                            model: suiteBackend.usersRows
                            textRole: "username"
                            displayText: currentIndex < 0 ? suiteBackend.uiText("USERS_SELECT_ACCOUNT") : currentText
                            currentIndex: -1
                        }
                        TextField {
                            id: usersChangeName
                            objectName: "usersChangeName"
                            Layout.fillWidth: true
                            placeholderText: suiteBackend.uiText("USERS_NEW_USERNAME")
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        TextField {
                            id: usersChangePassword
                            objectName: "usersChangePassword"
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            placeholderText: suiteBackend.uiText("USERS_NEW_PASSWORD")
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        ComboBox {
                            id: usersChangeRole
                            objectName: "usersChangeRole"
                            Layout.fillWidth: true
                            model: [{ "value": "", "label": suiteBackend.uiText("USERS_ROLE_UNCHANGED") }].concat(suiteBackend.usersRoleOptions)
                            textRole: "label"
                            valueRole: "value"
                        }
                        Button {
                            objectName: "usersChangeButton"
                            text: suiteBackend.uiText("USERS_APPLY")
                            enabled: !suiteBackend.usersBusy
                            onClicked: {
                                suiteBackend.updateUser(usersChangeAccount.currentIndex < 0 ? "" : usersChangeAccount.currentText, usersChangeName.text, usersChangePassword.text, usersChangeRole.currentValue)
                                usersChangePassword.text = ""
                            }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        spacing: 6
                        Text { text: suiteBackend.uiText("USERS_CREATE_TITLE"); color: window.cyan; font.bold: true; font.pixelSize: 12 }
                        TextField {
                            id: usersNewName
                            objectName: "usersNewName"
                            Layout.fillWidth: true
                            placeholderText: suiteBackend.uiText("USERS_COL_USERNAME")
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        TextField {
                            id: usersNewPassword
                            objectName: "usersNewPassword"
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            placeholderText: suiteBackend.uiText("USERS_NEW_PASSWORD")
                            color: window.textPrimary
                            background: Rectangle { radius: 8; color: window.panelAlt; border.width: 1; border.color: window.panelBorder }
                        }
                        ComboBox {
                            id: usersNewRole
                            objectName: "usersNewRole"
                            Layout.fillWidth: true
                            model: suiteBackend.usersRoleOptions
                            textRole: "label"
                            valueRole: "value"
                        }
                        Text { text: suiteBackend.uiText("USERS_ROLE_HINT"); color: window.muted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Button {
                            objectName: "usersCreateButton"
                            text: suiteBackend.uiText("USERS_CREATE_BUTTON")
                            enabled: !suiteBackend.usersBusy
                            onClicked: {
                                suiteBackend.createUser(usersNewName.text, usersNewPassword.text, usersNewRole.currentValue)
                                usersNewPassword.text = ""
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    Component {
        id: submittedModelsComponent
        ColumnLayout {
            width: contentLoader.width
            height: contentLoader.height
            spacing: 8
            FileDialog {
                id: modelUrdfSaveDialog
                property string category: ""
                property string slug: ""
                title: suiteBackend.uiText("MODELS_SAVE")
                fileMode: FileDialog.SaveFile
                nameFilters: ["URDF (*.urdf)"]
                onAccepted: suiteBackend.saveModelUrdf(modelUrdfSaveDialog.category, modelUrdfSaveDialog.slug, selectedFile.toString())
            }
            Text { text: suiteBackend.uiText("HEADING_SUBMITTED_MODELS"); color: window.cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 16 }
            Text {
                visible: !suiteBackend.modelsHasServer
                text: suiteBackend.uiText("LBL_ES_NO_ACTIVE_SERVER")
                color: window.muted
            }
            ColumnLayout {
                visible: suiteBackend.modelsHasServer
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8
                Text { text: suiteBackend.uiText("MODELS_INTRO"); color: window.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { visible: suiteBackend.modelsMessage !== ""; text: suiteBackend.modelsMessage; color: window.green; font.bold: true; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { visible: suiteBackend.modelsError !== ""; text: suiteBackend.modelsError; color: "#ee6b80"; font.bold: true; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { visible: suiteBackend.modelsError === "" && !suiteBackend.modelsBusy && suiteBackend.modelsRows.length === 0; text: suiteBackend.uiText("MODELS_NONE"); color: window.muted; font.pixelSize: 11 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: suiteBackend.uiText("MODELS_COL_NAME"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 200 }
                    Text { text: suiteBackend.uiText("MODELS_COL_CATEGORY"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.preferredWidth: 140 }
                    Text { text: suiteBackend.uiText("MODELS_COL_DATE"); color: "#556070"; font.bold: true; font.pixelSize: 10; Layout.fillWidth: true }
                    Button { objectName: "modelsRefreshButton"; text: suiteBackend.uiText("MODELS_REFRESH"); enabled: !suiteBackend.modelsBusy; onClicked: suiteBackend.refreshModels() }
                }
                ListView {
                    objectName: "modelsList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: suiteBackend.modelsRows
                    delegate: RowLayout {
                        required property var modelData
                        width: ListView.view.width
                        spacing: 8
                        Text { text: modelData.name; color: window.textPrimary; font.bold: true; font.pixelSize: 11; Layout.preferredWidth: 200; elide: Text.ElideRight }
                        Text { text: modelData.category; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.preferredWidth: 140; elide: Text.ElideRight }
                        Text { text: modelData.submitted; color: window.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                        Button {
                            objectName: "modelsSaveButton"
                            text: suiteBackend.uiText("MODELS_SAVE")
                            onClicked: { modelUrdfSaveDialog.category = modelData.category; modelUrdfSaveDialog.slug = modelData.slug; modelUrdfSaveDialog.open() }
                        }
                    }
                }
            }
        }
    }
}
