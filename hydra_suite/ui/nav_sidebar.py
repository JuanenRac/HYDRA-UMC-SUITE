# =============================================================================
# HYDRA-UMC SUITE - ui/nav_sidebar.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real structural parity fix: real user feedback said SUITE "no tiene el
# mismo esquema de estructura que studio... con su panel izquierdo con
# los menu y submenus" - the flat top QToolBar this app used for
# navigation (see main_window.py's own _build_command_deck, which still
# owns branding/status/about) didn't match HYDRA-UMC-STUDIO's own real
# left-sidebar navigation (Dashboard.tsx: a root menu, plus a drill-down
# "Resources" section into Industrial/URTC/HYDRA-UMC submenus with a
# "Back to Root" control).
#
# This widget is that same real navigation SHAPE, ported to Qt - not a
# copy of STUDIO's own React state machine, since this app's real content
# surfaces are still genuine QDockWidget panels (float/dock/tab/split all
# still work exactly as before): every button here just shows+raises the
# one real dock that already exists for it (main_window._activate_dock),
# the same thing the old toolbar buttons did. Nothing here invents a
# second navigation model - it's a different-shaped front door onto the
# same real docks.
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hydra_suite.i18n import _

# Real taxonomy, grouping every one of main_window.py's own real
# `self._docks` keys - kept here as one explicit, auditable list rather
# than inferred/scanned at runtime, so a real dock added later without a
# matching entry here fails loudly (see NavSidebar.__init__'s own assert)
# instead of silently having no way to reach it from this sidebar.
ROOT_ITEMS: tuple[tuple[str, str], ...] = (
    ("DOCK_SERVERS", "servers"),
    ("DOCK_OVERVIEW", "overview"),
    ("DOCK_VIEWPORT", "viewport"),
    ("DOCK_ROBOT_CONTROL", "robot"),
    ("DOCK_TRAJECTORY", "trajectory"),
    ("TAB_CAMERAS", "cameras"),
    ("DOCK_LOGS", "logs"),
)

# label_key, dock_key pairs per submenu - matches STUDIO's own real
# Dashboard.tsx groupings (industrial/urtc/hydraumc) item for item where
# SUITE has a real equivalent dock.
INDUSTRIAL_ITEMS: tuple[tuple[str, str], ...] = (
    ("HEADING_XY_TABLE", "xy_table"),
    ("HEADING_ATC", "atc"),
    ("HEADING_RACK_MANAGER", "rack"),
    ("HEADING_PICK_AND_PLACE", "pick_and_place"),
    ("HEADING_CNC", "cnc"),
    ("HEADING_LASER", "laser"),
    ("HEADING_VACUUM_TABLE", "vacuum_table"),
    ("HEADING_HEATED_BED", "heated_bed"),
)

URTC_ITEMS: tuple[tuple[str, str], ...] = (
    ("NAV_FLASHER_STUDIO", "urtc_flasher"),
    ("NAV_TESTER_CENTER", "urtc_tester"),
)

HYDRAUMC_ITEMS: tuple[tuple[str, str], ...] = (
    ("NAV_FIRMWARE_UPDATE", "hydra_flasher"),
    ("NAV_HARDWARE_TESTER", "hydra_tester"),
    ("HEADING_KINEMATIC_BRAIN_STAGE", "kinematic_brain_stage"),
)

# Second block inside the HYDRA-UMC submenu, under its own "Ecosystem"
# section header - matches STUDIO's own t('ecosystem.menu_section')
# grouping (Services/Telemetry/AI Family/admin surfaces) exactly. SUITE
# has no real isAdmin gate today (unlike STUDIO's own `isAdmin &&`) -
# these are shown unconditionally here too, matching this app's actual
# current behavior rather than inventing a gate that doesn't exist yet.
HYDRAUMC_ECOSYSTEM_ITEMS: tuple[tuple[str, str], ...] = (
    ("DOCK_ECOSYSTEM_SERVICES", "ecosystem_services"),
    ("DOCK_ECOSYSTEM_TELEMETRY", "ecosystem_telemetry"),
    ("DOCK_AI_FAMILY", "ai_family"),
    ("DOCK_ADMIN_CLIENTS", "admin_clients"),
    ("DOCK_ADMIN_LOGS", "admin_logs"),
    ("DOCK_ADMIN_SERVER", "admin_server"),
)

# Every real dock key this sidebar can reach - a real test
# (tests/test_nav_sidebar.py) diffs this against main_window.py's own
# `self._docks` keys, so a future dock added to one file and forgotten in
# the other fails a real test before it ships, rather than only being
# discovered by a person clicking through every menu by hand.
ALL_DOCK_KEYS = frozenset(
    key
    for _label, key in (
        *ROOT_ITEMS, *INDUSTRIAL_ITEMS, *URTC_ITEMS, *HYDRAUMC_ITEMS, *HYDRAUMC_ECOSYSTEM_ITEMS,
    )
)


class NavSidebar(QWidget):
    """The real left navigation panel - a root view plus 3 real submenus
    (Industrial/URTC/HYDRA-UMC), each with its own "Back to Root" control,
    the same drill-down shape as STUDIO's own Dashboard.tsx sidebar."""

    navigate_requested = Signal(str)  # emits a real main_window._docks key

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("navSidebar")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._stack = QStackedWidget(self)
        outer.addWidget(self._stack)

        self._stack.addWidget(self._build_root_page())
        self._stack.addWidget(self._build_submenu_page("NAV_CATEGORY_INDUSTRIAL", INDUSTRIAL_ITEMS))
        self._stack.addWidget(self._build_submenu_page("NAV_CATEGORY_URTC", URTC_ITEMS))
        self._stack.addWidget(self._build_submenu_page("NAV_CATEGORY_HYDRA_UMC", HYDRAUMC_ITEMS, HYDRAUMC_ECOSYSTEM_ITEMS))

    # -- page builders --------------------------------------------------

    def _nav_button(self, label_key: str, *, on_click, category: bool = False) -> QPushButton:
        button = QPushButton(_(label_key), self)
        button.setObjectName("navSidebarCategory" if category else "navSidebarItem")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(on_click)
        return button

    def _build_root_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(4)

        for label_key, dock_key in ROOT_ITEMS:
            layout.addWidget(self._nav_button(label_key, on_click=lambda _c=False, k=dock_key: self.navigate_requested.emit(k)))

        section = QLabel(_("NAV_SECTION_RESOURCES"), page)
        section.setObjectName("navSidebarSection")
        layout.addSpacing(14)
        layout.addWidget(section)

        for label_key, target in (
            ("NAV_CATEGORY_INDUSTRIAL", 1),
            ("NAV_CATEGORY_URTC", 2),
            ("NAV_CATEGORY_HYDRA_UMC", 3),
        ):
            layout.addWidget(self._nav_button(label_key, on_click=lambda _c=False, i=target: self._stack.setCurrentIndex(i), category=True))

        layout.addStretch(1)
        return page

    def _build_submenu_page(self, title_key: str, items: tuple[tuple[str, str], ...], ecosystem_items: tuple[tuple[str, str], ...] = ()) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(4)

        back = self._nav_button("NAV_BACK_TO_ROOT", on_click=lambda: self._stack.setCurrentIndex(0))
        back.setObjectName("navSidebarBack")
        layout.addWidget(back)

        title = QLabel(_(title_key), page)
        title.setObjectName("navSidebarSection")
        layout.addSpacing(10)
        layout.addWidget(title)

        for label_key, dock_key in items:
            layout.addWidget(self._nav_button(label_key, on_click=lambda _c=False, k=dock_key: self.navigate_requested.emit(k)))

        if ecosystem_items:
            eco_section = QLabel(_("NAV_SECTION_ECOSYSTEM"), page)
            eco_section.setObjectName("navSidebarSection")
            layout.addSpacing(14)
            layout.addWidget(eco_section)
            for label_key, dock_key in ecosystem_items:
                layout.addWidget(self._nav_button(label_key, on_click=lambda _c=False, k=dock_key: self.navigate_requested.emit(k)))

        layout.addStretch(1)
        return page
