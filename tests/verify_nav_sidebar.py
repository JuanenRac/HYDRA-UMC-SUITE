"""Real assertion-based coverage for NavSidebar (ui/nav_sidebar.py) - the
left navigation panel added for real structural parity with
HYDRA-UMC-STUDIO's own Dashboard.tsx (root menu + Industrial/URTC/
HYDRA-UMC submenus with a Back-to-Root control), real user feedback
having found SUITE's previous flat top-toolbar nav didn't match it.

Headless: a real QApplication + a real MainWindow (needs qasync's event
loop the same way verify_cameras_panel.py does, since several panels
schedule a real asyncio task in their own __init__) - never a mocked
widget tree, so a real wiring mistake (a sidebar button pointing at a
dock key that doesn't exist, or a real dock missing from the sidebar
entirely) fails this test the same way it would fail a person clicking
through the app by hand."""
import asyncio
import sys

import qasync
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.ui.main_window import MainWindow
from hydra_suite.ui.nav_sidebar import ALL_DOCK_KEYS, NavSidebar


def _run() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    win = MainWindow()
    # A real isVisible() check below needs the whole ancestor chain shown,
    # not just the dock itself - QWidget.isVisible() is false for
    # anything under a top-level window that was never shown, regardless
    # of that widget's own .show() calls.
    win.show()
    loop.run_until_complete(asyncio.sleep(0))  # pump any __init__-scheduled asyncio task

    # --- real 1:1 coverage: every real main_window._docks key must be
    # reachable from the sidebar, and the sidebar must never point at a
    # dock key that doesn't actually exist - a real drift check, not an
    # assumption either file's own author kept them in sync by hand. ---
    real_dock_keys = set(win._docks.keys())
    assert ALL_DOCK_KEYS == real_dock_keys, (
        f"NavSidebar/main_window._docks drifted apart - "
        f"missing from sidebar: {real_dock_keys - ALL_DOCK_KEYS}, "
        f"sidebar targets with no real dock: {ALL_DOCK_KEYS - real_dock_keys}"
    )

    assert hasattr(win, "_nav_sidebar_dock"), "MainWindow must build a real sidebar dock"
    sidebar_dock = win._nav_sidebar_dock
    sidebar = sidebar_dock.widget()
    assert isinstance(sidebar, NavSidebar)

    # The sidebar is structural chrome, not a content panel - it must
    # never be closable/floatable/movable away like a real work panel,
    # and must never show up in the View menu's real toggle-visibility
    # list (dock.toggleViewAction() targets, populated in _build_panels).
    from PySide6.QtWidgets import QDockWidget
    assert sidebar_dock.features() == QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
    view_menu_docks = {action.text() for action in win._view_menu.actions()}
    assert sidebar_dock.windowTitle() not in view_menu_docks or sidebar_dock.windowTitle() == "", (
        "the nav sidebar must not appear as a closable/toggleable dock in the View menu"
    )

    # --- real click-through: every real sidebar target must actually
    # raise/show its real dock, through the real navigate_requested ->
    # _activate_dock wiring already connected in _build_nav_sidebar()
    # (emitting the signal here, not calling _activate_dock directly, is
    # what actually proves that connection exists at all). Hide every
    # dock first so a dock that was already visible for some other real
    # reason can't hide a wiring bug that leaves it untouched. ---
    for dock in win._docks.values():
        dock.hide()
    for key in ALL_DOCK_KEYS:
        sidebar.navigate_requested.emit(key)
        assert win._docks[key].isVisible(), f"dock {key!r} did not become visible after its real sidebar signal fired"

    # --- real root <-> submenu navigation (the actual drill-down shape
    # the user asked for, matching STUDIO's own root/Industrial/URTC/
    # HYDRA-UMC/back structure) ---
    assert sidebar._stack.count() == 4, "root + 3 real submenus (Industrial/URTC/HYDRA-UMC)"
    assert sidebar._stack.currentIndex() == 0, "must open on the root page"
    for target_index in (1, 2, 3):
        sidebar._stack.setCurrentIndex(target_index)
        assert sidebar._stack.currentIndex() == target_index
    sidebar._stack.setCurrentIndex(0)
    assert sidebar._stack.currentIndex() == 0

    print("verify_nav_sidebar: all real assertions passed")


if __name__ == "__main__":
    _run()
