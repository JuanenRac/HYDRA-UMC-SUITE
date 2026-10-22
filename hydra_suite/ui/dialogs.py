# =============================================================================
# HYDRA-UMC SUITE - ui/dialogs.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Dialogs that do not run their own event loop. A dialog opened with exec()
# or one of the static QMessageBox / QInputDialog helpers spins a nested loop;
# started from inside a coroutine that blocks the asyncio task under qasync
# while timers and sockets keep firing. These helpers show the dialog with
# open() (window modal, returns at once) and hand the answer to a callback, so
# nothing waits inside a task.
# =============================================================================
from __future__ import annotations

from typing import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

_ICONS = {
    "information": QMessageBox.Icon.Information,
    "warning": QMessageBox.Icon.Warning,
    "critical": QMessageBox.Icon.Critical,
}


def show_message(parent: QWidget | None, kind: str, title: str, text: str) -> QMessageBox:
    """An information / warning / critical box that returns at once."""
    box = QMessageBox(_ICONS.get(kind, QMessageBox.Icon.Information), title, text, QMessageBox.StandardButton.Ok, parent)
    box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    box.setWindowModality(Qt.WindowModality.WindowModal)
    box.open()
    return box


def confirm(parent: QWidget | None, title: str, text: str, on_yes: Callable[[], None]) -> QMessageBox:
    """A Yes / No question; `on_yes` runs only when the answer is Yes."""
    box = QMessageBox(QMessageBox.Icon.Question, title, text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, parent)
    box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    box.setWindowModality(Qt.WindowModality.WindowModal)
    box.finished.connect(lambda result: on_yes() if result == QMessageBox.StandardButton.Yes else None)
    box.open()
    return box


def ask_text(parent: QWidget | None, title: str, label: str, default: str, on_text: Callable[[str], None]) -> QInputDialog:
    """A one-line text prompt; `on_text` runs with the text when accepted."""
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(default)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.textValueSelected.connect(on_text)
    dialog.open()
    return dialog


def ask_item(parent: QWidget | None, title: str, label: str, items: Sequence[str], on_item: Callable[[str], None]) -> QInputDialog:
    """A choice from a list; `on_item` runs with the chosen entry when accepted."""
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setComboBoxItems(list(items))
    dialog.setComboBoxEditable(False)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.textValueSelected.connect(on_item)
    dialog.open()
    return dialog
