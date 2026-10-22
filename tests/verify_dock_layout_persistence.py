# =============================================================================
# HYDRA-UMC-SUITE - dock layout persistence verifier
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The arrangement of the panels survives a restart: what is stored is encoded
# and decoded safely (a damaged or foreign value is ignored), a window built
# after a save comes up with the same panel closed, and View > Reset layout
# brings the default arrangement back. The configuration file is a temporary
# one, never the user's.
# =============================================================================
import asyncio
import sys
import tempfile
from pathlib import Path

import qasync
from PySide6.QtWidgets import QApplication

sys.path.insert(0, ".")
from hydra_suite import i18n
from hydra_suite.ui.layout_state import CONFIG_KEY, LAYOUT_VERSION, decode_layout, encode_layout
from hydra_suite.ui.main_window import MainWindow


def check(label: str, condition: bool) -> None:
    assert condition, label


def pure_cases() -> None:
    state = bytes(range(200))
    check("round trip", decode_layout(encode_layout(state)) == state)
    for bad in (None, 5, "x", [], {}, {"version": 99, "state": "AAAA"}, {"version": LAYOUT_VERSION}, {"version": LAYOUT_VERSION, "state": 7},
                {"version": LAYOUT_VERSION, "state": ""}, {"version": LAYOUT_VERSION, "state": "not base64!!"},
                {"version": LAYOUT_VERSION, "state": "A" * 600_000}):
        check(f"damaged value {str(bad)[:30]!r} is ignored", decode_layout(bad) is None)


def window_cases() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    with tempfile.TemporaryDirectory() as folder:
        i18n.CONFIG_FILE_PATH = Path(folder) / "config.json"
        first = MainWindow()
        first.show()
        loop.run_until_complete(asyncio.sleep(0))
        dock = first._docks["logs"]
        check("the logs dock starts visible", not dock.isHidden())
        dock.hide()
        first._save_dock_layout()
        check("the headless platform does not write the layout", i18n.load_config().get(CONFIG_KEY) is None)
        first._force_layout_save = True
        first._save_dock_layout()
        check("the layout was written", isinstance(i18n.load_config().get(CONFIG_KEY), dict))

        second = MainWindow()
        second.show()
        loop.run_until_complete(asyncio.sleep(0))
        check("the closed panel stays closed after a restart", second._docks["logs"].isHidden())

        second._reset_dock_layout()
        check("Reset layout shows it again", not second._docks["logs"].isHidden())
        check("Reset layout forgets the stored arrangement", i18n.load_config().get(CONFIG_KEY) is None)

        i18n.save_config({CONFIG_KEY: {"version": LAYOUT_VERSION, "state": "%%%garbage"}})
        third = MainWindow()
        third.show()
        loop.run_until_complete(asyncio.sleep(0))
        check("a damaged stored layout does not stop the window", not third._docks["logs"].isHidden())
        for window in (first, second, third):
            window.deleteLater()


def main() -> None:
    pure_cases()
    window_cases()
    print("verify_dock_layout_persistence: OK")


if __name__ == "__main__":
    main()
