"""Real assertion-based coverage for RobotView.atc/set_atc/has_xy_table
(models.py) and AtcToolsPanel (ui/panels/atc_tools_panel.py). Headless: a
real QApplication + qasync loop, no network connection, feeding a real
HydraState through SuiteController.active_state_changed the same way a
real WS/REST update would - not mocked at the Qt layer, only the network
is never actually opened. Same convention as verify_module_config_panel.py."""
import asyncio
import sys

import qasync
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite.app import SuiteController
from hydra_suite.models import HydraState, RobotView
from hydra_suite.ui.panels.atc_tools_panel import AtcToolsPanel, _default_atc_config, _default_pos


def _state_with_one_robot(atc: dict | None = None, has_xy_table: bool = False) -> HydraState:
    robot: dict = {"id": 1, "model": "Generic (6-DOF)", "role": "Idle", "hasXYTable": has_xy_table}
    if atc is not None:
        robot["atc"] = atc
    return HydraState(
        {
            "activeControllerId": "c1",
            "controllers": [{"id": "c1", "robots": [robot]}],
        }
    )


def _run() -> None:
    # --- RobotView.atc/set_atc/has_xy_table -------------------------------
    robot = RobotView({"id": 1})
    assert robot.atc is None, "atc must be None when absent, never {}/KeyError"
    assert robot.has_xy_table is False

    robot.set_atc({"type": "revolver", "revolverSlots": 8, "tools": []})
    assert robot.atc is not None
    assert robot.atc["type"] == "revolver"

    robot.set_atc(None)
    assert robot.atc is None, "set_atc(None) must remove the key entirely, matching STUDIO's `atc: undefined`"
    assert "atc" not in robot.raw
    print("RobotView.atc/set_atc/has_xy_table: PASS")

    # --- AtcToolsPanel, headless, real Qt widgets --------------------------
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    controller = SuiteController()
    panel = AtcToolsPanel(controller)

    # No ATC configured yet - the empty-state page.
    controller.active_state_changed.emit(_state_with_one_robot(atc=None))
    assert panel._stack.currentIndex() == 0, "no atc block yet -> empty-state page"
    assert panel._current_robot is not None

    # Real enable click - default config, vertical_panel/2x2 (4 slots).
    panel._on_enable()
    assert panel._current_robot.atc is not None
    assert panel._stack.currentIndex() == 1, "enabling must switch to the settings page"
    assert panel._current_robot.atc == _default_atc_config()
    print("AtcToolsPanel enable -> default config (vertical_panel/2x2): PASS")

    # Assign a real tool to slot 0.
    panel._on_tool_changed(0, "Drill (BL4260)")
    tools = panel._current_robot.atc["tools"]
    assert len(tools) == 1
    assert tools[0] == {"slot": 0, "tool": "Drill (BL4260)", "pos": _default_pos()}
    print("AtcToolsPanel tool assignment writes slot/tool/default pos: PASS")

    # Editing that slot's position writes into the right tool entry.
    panel._on_pos_field_changed(0, "j1", 45.0)
    panel._on_pos_field_changed(0, "j2", -30.0)
    tools = panel._current_robot.atc["tools"]
    assert tools[0]["pos"]["j1"] == 45.0
    assert tools[0]["pos"]["j2"] == -30.0
    print("AtcToolsPanel per-slot position edits: PASS")

    # Changing the grid clears tool assignments, matching STUDIO's own
    # handleGridChange() (`updateAtcConfig({ panelGrid: grid, tools: [] })`).
    panel._grid_combo.setCurrentIndex(panel._grid_combo.findData("3x3"))
    assert panel._current_robot.atc["panelGrid"] == "3x3"
    assert panel._current_robot.atc["tools"] == [], "grid change must clear tool assignments, matching STUDIO"
    print("AtcToolsPanel grid change clears tools: PASS")

    # Switching to revolver mode + capacity + base pickup position.
    panel._on_type_changed("revolver")
    assert panel._current_robot.atc["type"] == "revolver"
    # isHidden() (this widget's own explicit shown/hidden flag) rather than
    # isVisible() (also gated by every ancestor actually being on screen,
    # which nothing in this headless test - no panel.show() - ever is).
    assert panel._panel_group.isHidden() is True
    assert panel._revolver_group.isHidden() is False

    panel._revolver_spin.setValue(12)
    assert panel._current_robot.atc["revolverSlots"] == 12
    assert panel._current_robot.atc["tools"] == [], "revolver slot count change must clear tool assignments too"

    panel._on_pos_field_changed("revolver", "tx", 12.5)
    assert panel._current_robot.atc["revolverPos"]["tx"] == 12.5
    print("AtcToolsPanel revolver type/capacity/base-pos: PASS")

    # Reset returns to the real default config.
    panel._on_reset()
    assert panel._current_robot.atc == _default_atc_config()
    print("AtcToolsPanel reset -> default config: PASS")

    # Remove clears the whole block.
    panel._on_disable()
    assert panel._current_robot.atc is None
    assert panel._stack.currentIndex() == 0
    print("AtcToolsPanel remove -> atc cleared, empty-state page: PASS")

    # --- has_xy_table gating on the position editor -----------------------
    controller.active_state_changed.emit(_state_with_one_robot(atc=_default_atc_config(), has_xy_table=True))
    assert panel._current_robot.has_xy_table is True
    panel._on_toggle_slot_pos(0)
    editor = panel._slot_pos_editors.get(0)
    assert editor is not None
    assert "tx" in editor._spins and "ty" in editor._spins, "hasXYTable=True must add the table tx/ty fields"
    print("AtcToolsPanel position editor gates table tx/ty on hasXYTable: PASS")

    print("ALL VERIFY_ATC_TOOLS_PANEL CHECKS PASSED")


if __name__ == "__main__":
    _run()
