# =============================================================================
# HYDRA-UMC SUITE - tests/verify_no_nested_loops.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# A modal dialog that runs its own event loop (exec(), QMessageBox.question(),
# QInputDialog.getText(), QFileDialog.get...) must not be started from inside
# a coroutine: under qasync it blocks the running asyncio task while timers
# and sockets keep firing. This checks the source of every UI module for such
# a call inside an `async def`, and checks the non-blocking dialog helpers.
# Run headless: QT_QPA_PLATFORM=offscreen.
# =============================================================================
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication, QMessageBox

from hydra_suite.ui.dialogs import ask_item, ask_text, confirm, show_message

failures = 0


def check(label, actual, expected):
    global failures
    if actual != expected:
        print(f"FAIL {label}: expected {expected!r}, got {actual!r}")
        failures += 1
    else:
        print(f"ok   {label}")


BLOCKING_STATIC = {
    ("QMessageBox", "question"), ("QMessageBox", "information"), ("QMessageBox", "warning"), ("QMessageBox", "critical"),
    ("QInputDialog", "getText"), ("QInputDialog", "getItem"), ("QInputDialog", "getInt"), ("QInputDialog", "getDouble"),
    ("QFileDialog", "getOpenFileName"), ("QFileDialog", "getSaveFileName"), ("QFileDialog", "getExistingDirectory"),
}


def blocking_calls_in_coroutines(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.AsyncFunctionDef):
            continue
        for node in ast.walk(func):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            attr = node.func.attr
            owner = node.func.value.id if isinstance(node.func.value, ast.Name) else None
            if attr == "exec" or (owner, attr) in BLOCKING_STATIC:
                found.append(f"{path.relative_to(ROOT)}:{node.lineno} {func.name}")
    return found


offenders = []
for path in sorted((ROOT / "hydra_suite" / "ui").rglob("*.py")):
    offenders += blocking_calls_in_coroutines(path)
check("no dialog with its own loop inside a coroutine", offenders, [])

app = QApplication.instance() or QApplication(sys.argv)

box = show_message(None, "information", "t", "x")
check("show_message returns at once, window modal and shown", box.isVisible(), True)
box.close()

answers = []
yes = confirm(None, "t", "x", lambda: answers.append("yes"))
yes.button(QMessageBox.StandardButton.No).click()
check("confirm: No does nothing", answers, [])
yes = confirm(None, "t", "x", lambda: answers.append("yes"))
yes.button(QMessageBox.StandardButton.Yes).click()
check("confirm: Yes calls back", answers, ["yes"])

texts = []
dialog = ask_text(None, "t", "label", "default", texts.append)
check("ask_text: shows the default", dialog.textValue(), "default")
dialog.setTextValue("name")
dialog.accept()
check("ask_text: accepted text reaches the callback", texts, ["name"])

items = []
dialog = ask_item(None, "t", "label", ["a.json", "b.json"], items.append)
dialog.setTextValue("b.json")
dialog.accept()
check("ask_item: the chosen entry reaches the callback", items, ["b.json"])

dialog = ask_item(None, "t", "label", ["a.json"], items.append)
dialog.reject()
check("ask_item: cancelling calls nothing", items, ["b.json"])

print("FAILURES:", failures)
sys.exit(1 if failures else 0)
